"""Tests for bootstrap.sh, the curl | bash fresh-machine entrypoint."""

import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / 'bootstrap.sh'

FAKE_CLI_TOOLS_SH = """\
echo cli-tools.sh >> "${CALL_LOG}"
cat > "${INSTALL_BIN}/just" <<'EOF'
#!/usr/bin/env bash
echo "just $*" >> "${CALL_LOG}"
EOF
chmod +x "${INSTALL_BIN}/just"
"""


def write_executable(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f'#!/usr/bin/env bash\n{body}')
    path.chmod(0o755)


class Machine:
    """Fake fresh machine: stubbed sudo/git, empty $HOME, no `just` on PATH.

    install_bin stands in for /usr/local/bin: on PATH, empty until cli-tools.
    """

    def __init__(self, tmp_path: Path) -> None:
        self.home = tmp_path / 'home'
        self.home.mkdir()
        self.stub_bin = tmp_path / 'stub_bin'
        self.install_bin = tmp_path / 'install_bin'
        self.install_bin.mkdir()
        self.call_log = tmp_path / 'calls.log'
        self.call_log.touch()
        self.dotfiles_dir = self.home / 'projects' / 'dotfiles'
        self.upstream = tmp_path / 'upstream'
        self.build_upstream()
        write_executable(
            self.stub_bin / 'sudo',
            'echo "sudo $*" >> "${CALL_LOG}"\n',
        )
        write_executable(
            self.stub_bin / 'git',
            'echo "git $1" >> "${CALL_LOG}"\n'
            '[[ "$1" == clone ]] && '
            'cp -r "${UPSTREAM}" "${3:-$(basename "$2")}"\n'
            'true\n',
        )

    def build_upstream(self, apt_sh_extra: str = '') -> None:
        shutil.rmtree(self.upstream, ignore_errors=True)
        install = self.upstream / 'install'
        install.mkdir(parents=True)
        (self.upstream / '.git').mkdir()
        write_executable(
            install / 'apt.sh',
            f'echo apt.sh >> "${{CALL_LOG}}"\n{apt_sh_extra}',
        )
        write_executable(install / 'cli-tools.sh', FAKE_CLI_TOOLS_SH)

    def env(self, **extra: str) -> dict[str, str]:
        return {
            'HOME': str(self.home),
            'PATH': f'{self.stub_bin}:{self.install_bin}:/usr/bin:/bin',
            'INSTALL_BIN': str(self.install_bin),
            'CALL_LOG': str(self.call_log),
            'UPSTREAM': str(self.upstream),
            **extra,
        }

    def run(
        self,
        extra_env: dict[str, str] | None = None,
        *,
        piped: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        """Run the script, optionally as `curl ... | bash` would (via stdin).

        A new session detaches from any controlling terminal, so /dev/tty is
        unavailable -- as in CI -- no matter where the tests are run from.
        """
        return subprocess.run(  # noqa: S603
            ['/usr/bin/env', 'bash']
            if piped
            else ['/usr/bin/env', 'bash', str(SCRIPT)],
            input=SCRIPT.read_text() if piped else '',
            env=self.env(**(extra_env or {})),
            capture_output=True,
            text=True,
            check=False,
            start_new_session=True,
        )

    def calls(self) -> list[str]:
        return self.call_log.read_text().splitlines()


@pytest.fixture
def machine(tmp_path: Path) -> Machine:
    return Machine(tmp_path)


def test_fresh_machine_installs_just_before_running_bootstrap(
    machine: Machine,
) -> None:
    result = machine.run()

    assert result.returncode == 0, result.stderr
    calls = machine.calls()
    assert 'git clone' in calls
    assert calls[calls.index('git clone') + 1 :] == [
        'apt.sh',
        'cli-tools.sh',
        'just bootstrap',
        'just ',
    ]


def test_existing_projects_dir_and_clone_do_not_abort(
    machine: Machine,
) -> None:
    """The old bare `mkdir projects` failed under `set -e` on a re-run."""
    shutil.copytree(machine.upstream, machine.dotfiles_dir)

    result = machine.run()

    assert result.returncode == 0, result.stderr
    assert 'git clone' not in machine.calls()
    assert 'just bootstrap' in machine.calls()


def test_skips_just_prerequisites_when_just_is_already_installed(
    machine: Machine,
) -> None:
    write_executable(
        machine.stub_bin / 'just',
        'echo "just $*" >> "${CALL_LOG}"\n',
    )

    result = machine.run()

    assert result.returncode == 0, result.stderr
    calls = machine.calls()
    assert not {'apt.sh', 'cli-tools.sh'} & set(calls)
    assert 'just bootstrap' in calls


@pytest.mark.parametrize(
    ('extra_env', 'expected_call'),
    [
        ({}, 'just bootstrap'),
        ({'DOTFILES_BOOTSTRAP_RECIPE': '_ci'}, 'just _ci'),
    ],
)
def test_runs_the_requested_bootstrap_recipe(
    machine: Machine,
    extra_env: dict[str, str],
    expected_call: str,
) -> None:
    result = machine.run(extra_env)

    assert result.returncode == 0, result.stderr
    assert expected_call in machine.calls()


def test_curl_pipe_survives_a_step_that_reads_stdin(machine: Machine) -> None:
    """Under `curl | bash`, a step reading stdin eats the rest of the script.

    Wrapping the body in main() makes bash parse it all before running any.
    """
    machine.build_upstream(apt_sh_extra='cat > /dev/null\n')

    result = machine.run(piped=True)

    assert result.returncode == 0, result.stderr
    assert machine.calls()[-2:] == ['just bootstrap', 'just ']
