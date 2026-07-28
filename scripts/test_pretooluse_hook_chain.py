"""Tests for the combined atuin+cartoon PreToolUse hook."""

import subprocess

import pytest

from pretooluse_hook_chain import main, run_atuin, run_cartoon

RAW_PAYLOAD = '{"tool_name": "Bash", "tool_input": {"command": "echo hi"}}'


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
