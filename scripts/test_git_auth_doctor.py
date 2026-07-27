"""Integration tests for scripts/git_auth_doctor.sh.

The doctor is driven against a throwaway repo with `curl`, `ssh`, `ssh-add`
and `gh` stubbed on PATH, so nothing here touches the network or the real
ssh-agent.
"""

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).parent
DOCTOR = SCRIPTS_DIR / 'git_auth_doctor.sh'
GIT = shutil.which('git') or 'git'

ORG_SSH = 'git@github.com:AcmeEngineering/acme-aws.git'
ORG_HTTPS = 'https://github.com/AcmeEngineering/acme-aws.git'
PERSONAL_HTTPS = 'https://github.com/dannybrown37/dotfiles.git'

WORK_TOKEN = 'ghp_work_000000000000000000000000000000'  # noqa: S105
PERSONAL_TOKEN = 'ghp_personal_00000000000000000000000000'  # noqa: S105

CURL_STUB = """#!/usr/bin/env bash
set -uo pipefail

headers_file=""
url=""
prev=""
for arg in "$@"; do
    [[ "${prev}" == "-D" ]] && headers_file="${arg}"
    [[ "${arg}" == https://* ]] && url="${arg}"
    prev="${arg}"
done

case "${url}" in
*/user)
    {
        printf 'HTTP/2 %s\\r\\n' "${STUB_USER_STATUS:-200}"
        printf 'x-oauth-scopes: %s\\r\\n' "${STUB_SCOPES-repo, workflow}"
        printf '\\r\\n'
    } >"${headers_file}"
    printf '{"login":"%s"}' "${STUB_USER_LOGIN:-nobody}"
    ;;
*/repos/*)
    {
        printf 'HTTP/2 %s\\r\\n' "${STUB_REPO_STATUS:-200}"
        if [[ -n "${STUB_SSO:-}" ]]; then
            printf 'x-github-sso: required; url=https://github.com/orgs/x/sso\\r\\n'
        fi
        printf '\\r\\n'
    } >"${headers_file}"
    perms='{"permissions":{"admin":false,"push":%s,"pull":true}}'
    printf "${perms}" "${STUB_REPO_PUSH:-true}"
    ;;
esac
"""

# Real ssh writes the GitHub greeting to stderr and exits non-zero either way,
# so a stub that exited 0 on success would not exercise the parsing.
SSH_STUB = """#!/usr/bin/env bash
if [[ -n "${STUB_SSH_OK:-}" ]]; then
    echo "Hi ${STUB_SSH_LOGIN:-acmebrownwork}! You've successfully" \
         "authenticated, but GitHub does not provide shell access." >&2
    exit 1
fi
echo "git@github.com: Permission denied (publickey)." >&2
exit 255
"""

SSH_ADD_STUB = """#!/usr/bin/env bash
if [[ -n "${STUB_AGENT_KEYS:-}" ]]; then
    echo "256 SHA256:abc123 danny@wsl (ED25519)"
    exit 0
fi
echo "The agent has no identities." >&2
exit 1
"""

GH_STUB = """#!/usr/bin/env bash
[[ "${2:-}" == "git-credential" ]] || exit 0
[[ "${3:-}" == "get" ]] || exit 0
echo "username=x-access-token"
echo "password=${STUB_GH_TOKEN:-}"
"""

PERSONAL_HELPER_STUB = """#!/usr/bin/env bash
[[ "${1:-}" == "get" ]] || exit 0
echo "username=dannybrown37"
echo "password=${STUB_PERSONAL_TOKEN:-}"
"""


class DoctorHarness:
    """A throwaway repo plus stubbed binaries to run the doctor against."""

    def __init__(self, root: Path) -> None:
        self.home = root / 'home'
        self.repo = root / 'repo'
        self.bin = root / 'bin'
        for path in (self.home, self.repo, self.bin):
            path.mkdir(parents=True)

    def install_stub(self, name: str, body: str) -> Path:
        path = self.bin / name
        path.write_text(body)
        path.chmod(0o755)
        return path

    def write_gitconfig(self, helper: str) -> None:
        # The includeIf targets are symlinks in the real setup; the doctor
        # warns when they are plain files, adding noise to every assertion.
        for name in ('.gitconfig-personal', '.gitconfig-private'):
            target = self.home / f'real{name}'
            target.write_text('')
            (self.home / name).symlink_to(target)
        (self.home / '.gitconfig').write_text(
            f'[credential "https://github.com"]\n\thelper = {helper}\n',
        )

    def init_repo(self, remote_url: str) -> None:
        subprocess.run([GIT, 'init', '-q'], cwd=self.repo, check=True)  # noqa: S603
        subprocess.run(  # noqa: S603
            [GIT, 'remote', 'add', 'origin', remote_url],
            cwd=self.repo,
            check=True,
        )

    def run(self, env_overrides: dict[str, str]) -> str:
        env = {**os.environ}
        for leaked in ('MY_GITHUB_TOKEN', 'GITHUB_TOKEN', 'MY_GITHUB_USER'):
            env.pop(leaked, None)
        env.update(
            {
                'HOME': str(self.home),
                'PATH': f'{self.bin}{os.pathsep}{os.environ["PATH"]}',
                'GIT_CONFIG_NOSYSTEM': '1',
                **env_overrides,
            },
        )
        result = subprocess.run(  # noqa: S603
            [str(DOCTOR), str(self.repo)],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        return result.stdout


CHECK_RE = re.compile(r'^\s*(✅|❌|⚠️)\s+(\S.*?)\s{2,}(.*)$')


def checks(output: str) -> dict[str, tuple[str, str]]:
    """Map each check's label to its (symbol, detail)."""
    found = {}
    for line in output.splitlines():
        match = CHECK_RE.match(line)
        if match:
            symbol, label, detail = match.groups()
            found[label.strip()] = (symbol, detail.strip())
    return found


def symbol_of(output: str, label: str) -> str:
    entry = checks(output).get(label)
    return entry[0] if entry else ''


@pytest.fixture
def harness(tmp_path: Path) -> DoctorHarness:
    h = DoctorHarness(tmp_path)
    h.install_stub('curl', CURL_STUB)
    h.install_stub('ssh', SSH_STUB)
    h.install_stub('ssh-add', SSH_ADD_STUB)
    h.install_stub('gh', GH_STUB)
    return h


@pytest.fixture
def org_repo(harness: DoctorHarness) -> DoctorHarness:
    harness.write_gitconfig('!gh auth git-credential')
    harness.init_repo(ORG_HTTPS)
    return harness


@pytest.fixture
def ssh_repo(harness: DoctorHarness) -> DoctorHarness:
    harness.write_gitconfig('!gh auth git-credential')
    harness.init_repo(ORG_SSH)
    return harness


ORG_ENV = {
    'GITHUB_TOKEN': WORK_TOKEN,
    'MY_GITHUB_TOKEN': PERSONAL_TOKEN,
    'STUB_GH_TOKEN': WORK_TOKEN,
    'STUB_USER_LOGIN': 'acmebrownwork',
}


class TestSshRemote:
    """An SSH remote must be diagnosed as SSH, not as a broken HTTPS chain."""

    def test_recommends_the_exact_https_switch_command(
        self,
        ssh_repo: DoctorHarness,
    ) -> None:
        output = ssh_repo.run(ORG_ENV)
        assert f'git remote set-url origin {ORG_HTTPS}' in output

    def test_summary_repeats_the_command_when_https_would_work(
        self,
        ssh_repo: DoctorHarness,
    ) -> None:
        output = ssh_repo.run(ORG_ENV)
        summary = (
            output.rsplit('Summary', 1)[-1] if 'Summary' in output else output
        )
        tail = summary.strip().splitlines()[-6:]
        assert any('git remote set-url origin' in line for line in tail), (
            output
        )

    def test_reports_the_ssh_failure_itself(
        self,
        ssh_repo: DoctorHarness,
    ) -> None:
        output = ssh_repo.run(ORG_ENV)
        assert symbol_of(output, 'ssh auth') == '❌'
        assert 'publickey' in checks(output)['ssh auth'][1]

    def test_reports_an_empty_agent(self, ssh_repo: DoctorHarness) -> None:
        output = ssh_repo.run(ORG_ENV)
        assert symbol_of(output, 'ssh-agent') == '❌'

    def test_working_ssh_key_passes(self, ssh_repo: DoctorHarness) -> None:
        output = ssh_repo.run(
            {**ORG_ENV, 'STUB_SSH_OK': '1', 'STUB_AGENT_KEYS': '1'},
        )
        assert symbol_of(output, 'ssh auth') == '✅'
        assert symbol_of(output, 'ssh-agent') == '✅'

    def test_does_not_blame_the_personal_helper(
        self,
        ssh_repo: DoctorHarness,
    ) -> None:
        """The bug that sent a real SSH push chasing credential helpers."""
        output = ssh_repo.run(ORG_ENV)
        assert symbol_of(output, 'helper script') != '❌'

    def test_https_chain_is_labelled_as_a_preview(
        self,
        ssh_repo: DoctorHarness,
    ) -> None:
        output = ssh_repo.run(ORG_ENV)
        assert 'preview' in output.lower()


class TestOrgRemoteExpectations:
    """A work/org remote should expect the gh helper, not the personal one."""

    def test_gh_helper_is_correct_for_an_org_remote(
        self,
        org_repo: DoctorHarness,
    ) -> None:
        output = org_repo.run(ORG_ENV)
        assert symbol_of(output, 'helper script') == '✅'

    def test_work_token_answering_is_correct_for_an_org_remote(
        self,
        org_repo: DoctorHarness,
    ) -> None:
        output = org_repo.run(ORG_ENV)
        assert symbol_of(output, 'token source') == '✅'

    def test_personal_token_answering_an_org_remote_is_a_failure(
        self,
        org_repo: DoctorHarness,
    ) -> None:
        output = org_repo.run({**ORG_ENV, 'STUB_GH_TOKEN': PERSONAL_TOKEN})
        assert symbol_of(output, 'token source') == '❌'

    def test_personal_remote_still_requires_the_personal_helper(
        self,
        harness: DoctorHarness,
    ) -> None:
        helper = harness.install_stub(
            'git-credential-personal.sh',
            PERSONAL_HELPER_STUB,
        )
        harness.write_gitconfig(f'!{helper}')
        harness.init_repo(PERSONAL_HTTPS)
        output = harness.run(
            {
                'GITHUB_TOKEN': WORK_TOKEN,
                'MY_GITHUB_TOKEN': PERSONAL_TOKEN,
                'STUB_PERSONAL_TOKEN': PERSONAL_TOKEN,
                'STUB_USER_LOGIN': 'dannybrown37',
            },
        )
        assert symbol_of(output, 'helper script') == '✅'
        assert symbol_of(output, 'token source') == '✅'

    def test_personal_remote_answered_by_work_token_still_fails(
        self,
        harness: DoctorHarness,
    ) -> None:
        harness.write_gitconfig('!gh auth git-credential')
        harness.init_repo(PERSONAL_HTTPS)
        output = harness.run(
            {
                'GITHUB_TOKEN': WORK_TOKEN,
                'MY_GITHUB_TOKEN': PERSONAL_TOKEN,
                'STUB_GH_TOKEN': WORK_TOKEN,
                'STUB_USER_LOGIN': 'acmebrownwork',
            },
        )
        assert symbol_of(output, 'helper script') == '❌'
        assert symbol_of(output, 'token source') == '❌'


class TestRepoAccess:
    """Replaces the login-vs-owner check, which failed on every org repo."""

    def test_org_repo_with_push_access_passes(
        self,
        org_repo: DoctorHarness,
    ) -> None:
        output = org_repo.run(ORG_ENV)
        assert symbol_of(output, 'repo access') == '✅'
        assert '403' not in output

    def test_account_login_is_reported_without_comparison(
        self,
        org_repo: DoctorHarness,
    ) -> None:
        output = org_repo.run(ORG_ENV)
        assert symbol_of(output, 'account') == '✅'
        assert 'acmebrownwork' in checks(output)['account'][1]

    def test_read_only_access_fails(self, org_repo: DoctorHarness) -> None:
        output = org_repo.run({**ORG_ENV, 'STUB_REPO_PUSH': 'false'})
        assert symbol_of(output, 'repo access') == '❌'

    def test_invisible_repo_fails(self, org_repo: DoctorHarness) -> None:
        output = org_repo.run({**ORG_ENV, 'STUB_REPO_STATUS': '404'})
        assert symbol_of(output, 'repo access') == '❌'

    def test_sso_requirement_is_called_out(
        self,
        org_repo: DoctorHarness,
    ) -> None:
        output = org_repo.run(
            {**ORG_ENV, 'STUB_REPO_STATUS': '403', 'STUB_SSO': '1'},
        )
        assert symbol_of(output, 'repo access') == '❌'
        assert 'SSO' in checks(output)['repo access'][1]


@pytest.mark.parametrize(
    ('scopes', 'expected'),
    [
        ('repo, workflow', '✅'),
        ('gist, read:user', '❌'),
        ('', '⚠️'),
    ],
)
def test_token_scope_reporting(
    org_repo: DoctorHarness,
    scopes: str,
    expected: str,
) -> None:
    output = org_repo.run({**ORG_ENV, 'STUB_SCOPES': scopes})
    assert symbol_of(output, 'token scopes') == expected


# ── Red-team regressions ────────────────────────────────────────────────────

ALIAS_SSH = 'git@github-work:AcmeEngineering/acme-aws.git'

# ~/.ssh/config Host aliases are the standard two-account SSH setup, and each
# alias can carry its own IdentityFile. This stub accepts only the alias.
ALIAS_ONLY_SSH_STUB = """#!/usr/bin/env bash
if [[ "${!#}" == *github-work ]]; then
    echo "Hi AcmeEngineering/acme-aws! You've successfully" \
         "authenticated, but GitHub does not provide shell access." >&2
    exit 1
fi
echo "git@github.com: Permission denied (publickey)." >&2
exit 255
"""

# The mirror image: the default key works, the alias the remote actually uses
# does not. A push would fail; the doctor must not report success.
DEFAULT_ONLY_SSH_STUB = """#!/usr/bin/env bash
if [[ "${!#}" == *github-work ]]; then
    echo "git@github-work: Permission denied (publickey)." >&2
    exit 255
fi
echo "Hi dannybrown37! You've successfully authenticated," \
     "but GitHub does not provide shell access." >&2
exit 1
"""

# GitHub documents the personal access token as either the username or the
# password of an HTTPS credential; git-credential-store entries written by a
# `https://<token>@github.com/...` clone use the username slot.
TOKEN_AS_USERNAME_HELPER_STUB = """#!/usr/bin/env bash
[[ "${1:-}" == "get" ]] || exit 0
echo "username=${STUB_PERSONAL_TOKEN:-}"
echo "password=x-oauth-basic"
"""  # noqa: S105

OLD_GIT_STUB = """#!/usr/bin/env bash
if [[ "${{1:-}}" == "--version" ]]; then
    echo "git version 2.25.1"
    exit 0
fi
exec {git} "$@"
"""


class TestSshHostAlias:
    """The doctor probes git@github.com regardless of what the remote uses."""

    def test_broken_alias_is_not_reported_as_working_ssh(
        self,
        harness: DoctorHarness,
    ) -> None:
        harness.install_stub('ssh', DEFAULT_ONLY_SSH_STUB)
        harness.write_gitconfig('!gh auth git-credential')
        harness.init_repo(ALIAS_SSH)
        output = harness.run({**ORG_ENV, 'STUB_AGENT_KEYS': '1'})
        assert symbol_of(output, 'ssh auth') != '✅', (
            'push over github-work alias fails, doctor said ssh auth is fine'
        )

    def test_working_alias_is_not_reported_as_broken_ssh(
        self,
        harness: DoctorHarness,
    ) -> None:
        harness.install_stub('ssh', ALIAS_ONLY_SSH_STUB)
        harness.write_gitconfig('!gh auth git-credential')
        harness.init_repo(ALIAS_SSH)
        output = harness.run({**ORG_ENV, 'STUB_AGENT_KEYS': '1'})
        assert symbol_of(output, 'ssh auth') != '❌'


@pytest.mark.parametrize(
    'remote_url',
    [
        ALIAS_SSH,
        'ssh://git@github.com:22/dannybrown37/dotfiles.git',
        'git@gitlab.com:group/sub/proj.git',
    ],
)
def test_never_recommends_a_remote_url_with_an_empty_owner(
    harness: DoctorHarness,
    remote_url: str,
) -> None:
    """A copy-pasteable set-url command must not point at github.com//repo."""
    harness.write_gitconfig('!gh auth git-credential')
    harness.init_repo(remote_url)
    output = harness.run(ORG_ENV)
    assert 'github.com//' not in output, output


def test_owner_case_difference_is_still_the_personal_account(
    harness: DoctorHarness,
) -> None:
    """GitHub logins are case-insensitive; both URL spellings push fine."""
    helper = harness.install_stub(
        'git-credential-personal.sh',
        PERSONAL_HELPER_STUB,
    )
    harness.write_gitconfig(f'!{helper}')
    harness.init_repo('https://github.com/DannyBrown37/dotfiles.git')
    output = harness.run(
        {
            'MY_GITHUB_TOKEN': PERSONAL_TOKEN,
            'STUB_PERSONAL_TOKEN': PERSONAL_TOKEN,
            'STUB_USER_LOGIN': 'dannybrown37',
        },
    )
    assert symbol_of(output, 'helper script') == '✅'
    assert symbol_of(output, 'token source') == '✅'


def test_no_credential_ever_reaches_stdout_verbatim(
    harness: DoctorHarness,
) -> None:
    """Output is safe to paste; username slot not exempt from redaction."""
    helper = harness.install_stub(
        'git-credential-personal.sh',
        TOKEN_AS_USERNAME_HELPER_STUB,
    )
    harness.write_gitconfig(f'!{helper}')
    harness.init_repo(PERSONAL_HTTPS)
    output = harness.run(
        {
            'MY_GITHUB_TOKEN': PERSONAL_TOKEN,
            'STUB_PERSONAL_TOKEN': PERSONAL_TOKEN,
            'STUB_USER_LOGIN': 'dannybrown37',
        },
    )
    assert PERSONAL_TOKEN not in output, output


def test_unrelated_failure_is_not_blamed_on_ssh(
    ssh_repo: DoctorHarness,
) -> None:
    """On Ubuntu 20.04, git 2.25 fails; SSH works fine, git is the problem."""
    ssh_repo.install_stub('git', OLD_GIT_STUB.format(git=GIT))
    output = ssh_repo.run(
        {**ORG_ENV, 'STUB_SSH_OK': '1', 'STUB_AGENT_KEYS': '1'},
    )
    summary = output.rsplit('Summary', 1)[-1]
    assert 'SSH is broken' not in summary, output
    assert 'SSH auth is broken' not in summary, output


@pytest.mark.parametrize(
    'scopes',
    ['repo:status, read:org', 'public_repo', 'read:repo_hook, gist'],
)
def test_repo_prefixed_scopes_do_not_count_as_push_access(
    org_repo: DoctorHarness,
    scopes: str,
) -> None:
    """None of these grant git push; all contain the substring 'repo'."""
    output = org_repo.run({**ORG_ENV, 'STUB_SCOPES': scopes})
    assert symbol_of(output, 'token scopes') != '✅', scopes
