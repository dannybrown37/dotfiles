"""Tests for the combined atuin+cartoon PreToolUse hook."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

from pretooluse_hook_chain import main, run_atuin, run_cartoon

RAW_PAYLOAD = '{"tool_name": "Bash", "tool_input": {"command": "echo hi"}}'
SCRIPT = Path(__file__).parent / 'pretooluse_hook_chain.py'


def run_script(
    bin_dir: Path,
    stdin: bytes = RAW_PAYLOAD.encode(),
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(  # noqa: S603
        [sys.executable, str(SCRIPT)],
        input=stdin,
        env={**os.environ, 'PATH': str(bin_dir)},
        capture_output=True,
        check=False,
    )


def fake_tool(bin_dir: Path, name: str, body: str) -> None:
    tool = bin_dir / name
    tool.write_text(f'#!/bin/sh\n{body}\n')
    tool.chmod(0o755)


def test_script_is_silent_when_neither_tool_is_installed(
    tmp_path: Path,
) -> None:
    result = run_script(tmp_path)

    assert (result.returncode, result.stdout, result.stderr) == (0, b'', b'')


@pytest.mark.parametrize(
    'cartoon_body',
    [
        pytest.param("printf '\\377\\376'", id='undecodable-output'),
        pytest.param('echo not json', id='non-json-output'),
        pytest.param('echo oops >&2; exit 3', id='crash'),
    ],
)
def test_script_is_silent_when_cartoon_misbehaves(
    tmp_path: Path,
    cartoon_body: str,
) -> None:
    fake_tool(tmp_path, 'cartoon', cartoon_body)
    fake_tool(tmp_path, 'atuin', "printf '\\377'; exit 1")

    result = run_script(tmp_path)

    assert (result.returncode, result.stdout, result.stderr) == (0, b'', b'')


def test_script_is_silent_on_undecodable_stdin(tmp_path: Path) -> None:
    result = run_script(tmp_path, stdin=b'\xff\xfe')

    assert (result.returncode, result.stdout, result.stderr) == (0, b'', b'')


def test_script_passes_cartoons_json_through(tmp_path: Path) -> None:
    rewrite = '{"hookSpecificOutput": {"hookEventName": "PreToolUse"}}'
    fake_tool(tmp_path, 'cartoon', f"echo '{rewrite}'")

    result = run_script(tmp_path)

    assert result.returncode == 0
    assert result.stdout.decode().strip() == rewrite


def test_run_cartoon_returns_none_on_undecodable_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        'pretooluse_hook_chain.shutil.which',
        lambda name: f'/usr/bin/{name}',
    )

    error = UnicodeDecodeError('utf-8', b'\xff', 0, 1, 'invalid start byte')

    def _raise(*_args: object, **_kwargs: object) -> None:
        raise error

    monkeypatch.setattr('pretooluse_hook_chain.subprocess.run', _raise)

    assert run_cartoon(RAW_PAYLOAD) is None


@pytest.mark.parametrize('stdout', ['not json', '[1, 2]', ''])
def test_run_cartoon_returns_none_unless_output_is_a_json_object(
    monkeypatch: pytest.MonkeyPatch,
    stdout: str,
) -> None:
    monkeypatch.setattr(
        'pretooluse_hook_chain.shutil.which',
        lambda name: f'/usr/bin/{name}',
    )
    monkeypatch.setattr(
        'pretooluse_hook_chain.subprocess.run',
        lambda *_a, **_k: _completed(0, stdout),
    )

    assert run_cartoon(RAW_PAYLOAD) is None


def _completed(
    returncode: int,
    stdout: str = '',
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=[],
        returncode=returncode,
        stdout=stdout,
        stderr='',
    )


@pytest.mark.parametrize('which_target', ['atuin', 'cartoon'])
def test_run_functions_skip_subprocess_when_binary_missing(
    monkeypatch: pytest.MonkeyPatch,
    which_target: str,
) -> None:
    monkeypatch.setattr(
        'pretooluse_hook_chain.shutil.which',
        lambda _name: None,
    )

    def _fail_if_called(
        *_args: object,
        **_kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        msg = 'subprocess.run should not be called when binary is missing'
        raise AssertionError(msg)

    monkeypatch.setattr(
        'pretooluse_hook_chain.subprocess.run',
        _fail_if_called,
    )

    if which_target == 'atuin':
        run_atuin(RAW_PAYLOAD)
    else:
        assert run_cartoon(RAW_PAYLOAD) is None


@pytest.mark.parametrize(
    'error',
    [FileNotFoundError, subprocess.TimeoutExpired],
)
def test_run_atuin_swallows_subprocess_failures(
    monkeypatch: pytest.MonkeyPatch,
    error: type[Exception],
) -> None:
    monkeypatch.setattr(
        'pretooluse_hook_chain.shutil.which',
        lambda _name: '/usr/bin/atuin',
    )

    def _raise(
        *_args: object,
        **_kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        if error is subprocess.TimeoutExpired:
            raise error(cmd='atuin', timeout=5)
        raise error

    monkeypatch.setattr('pretooluse_hook_chain.subprocess.run', _raise)

    run_atuin(RAW_PAYLOAD)


def test_run_cartoon_returns_stdout_on_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        'pretooluse_hook_chain.shutil.which',
        lambda _name: '/usr/bin/cartoon',
    )
    monkeypatch.setattr(
        'pretooluse_hook_chain.subprocess.run',
        lambda *_a, **_k: _completed(0, '{"hookSpecificOutput": {}}'),
    )

    assert run_cartoon(RAW_PAYLOAD) == '{"hookSpecificOutput": {}}'


def test_run_cartoon_returns_none_on_nonzero_exit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        'pretooluse_hook_chain.shutil.which',
        lambda _name: '/usr/bin/cartoon',
    )
    monkeypatch.setattr(
        'pretooluse_hook_chain.subprocess.run',
        lambda *_a, **_k: _completed(1, 'irrelevant'),
    )

    assert run_cartoon(RAW_PAYLOAD) is None


@pytest.mark.parametrize(
    'error',
    [FileNotFoundError, subprocess.TimeoutExpired],
)
def test_run_cartoon_returns_none_when_subprocess_fails(
    monkeypatch: pytest.MonkeyPatch,
    error: type[Exception],
) -> None:
    monkeypatch.setattr(
        'pretooluse_hook_chain.shutil.which',
        lambda _name: '/usr/bin/cartoon',
    )

    def _raise(
        *_args: object,
        **_kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        if error is subprocess.TimeoutExpired:
            raise error(cmd='cartoon', timeout=5)
        raise error

    monkeypatch.setattr('pretooluse_hook_chain.subprocess.run', _raise)

    assert run_cartoon(RAW_PAYLOAD) is None


def test_main_runs_atuin_and_prints_cartoons_rewrite(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        'pretooluse_hook_chain.run_atuin',
        lambda payload: calls.append(f'atuin:{payload}'),
    )
    monkeypatch.setattr(
        'pretooluse_hook_chain.run_cartoon',
        lambda payload: f'rewritten:{payload}',
    )

    exit_code = main(RAW_PAYLOAD)

    assert exit_code == 0
    assert calls == [f'atuin:{RAW_PAYLOAD}']
    assert capsys.readouterr().out == f'rewritten:{RAW_PAYLOAD}'


def test_main_prints_nothing_when_cartoon_has_no_rewrite(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        'pretooluse_hook_chain.run_atuin',
        lambda _payload: None,
    )
    monkeypatch.setattr(
        'pretooluse_hook_chain.run_cartoon',
        lambda _payload: None,
    )

    exit_code = main(RAW_PAYLOAD)

    assert exit_code == 0
    assert capsys.readouterr().out == ''
