"""fleet: parallel Claude Code and Copilot agents, one worktree each."""

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from fleet import VERSION, aws, jira, radar
from fleet.agents import AGENT_KINDS, validate_agent_name
from fleet.hooks_install import (
    CLAUDE_SETTINGS,
    claude_hooks_installed,
    install_claude_hooks,
    uninstall_claude_hooks,
)
from fleet.ops import (
    HOOK_PATH,
    LAUNCHER_PATH,
    SpawnRequest,
    agent_binary,
    dashboard_rows,
    default_agent_kind,
    default_store,
    default_tmux,
    ensure_dashboard,
    fleet_session,
    kill_agent,
    review_agent_kind,
    run_interactive,
    spawn_agent,
)
from fleet.palette import by_urgency
from fleet.procs import scan_agent_processes
from fleet.store import AgentRecord, default_state_dir
from fleet.work import (
    WorkItems,
    integration_status,
    live_fetchers,
    load_work_items,
)

USAGE_ERROR = 2
COPILOT_HOOK_LINK = Path.home() / '.copilot' / 'hooks' / 'fleet.json'


def prompt_tty(text: str, flag_hint: str) -> str:
    if not sys.stdin.isatty():
        msg = f'missing {flag_hint} (not prompting: stdin is not a TTY)'
        raise ValueError(msg)
    return input(text).strip()


def pick_agent_name(flag_hint: str) -> str:
    names = [record.name for record in default_store().list_records()]
    if not names:
        msg = 'no agents yet; start one with `fleet new NAME`'
        raise ValueError(msg)
    if not sys.stdin.isatty() or shutil.which('fzf') is None:
        msg = f'missing {flag_hint}; agents: {", ".join(names)}'
        raise ValueError(msg)
    picked = subprocess.run(
        ['fzf', '--prompt', 'agent> ', '--height', '40%', '--reverse'],  # noqa: S607
        input='\n'.join(names),
        stdout=subprocess.PIPE,
        text=True,
        check=False,
    ).stdout.strip()
    if not picked:
        msg = 'no agent picked'
        raise ValueError(msg)
    return picked


def find_record(name: str | None, flag_hint: str = 'NAME') -> AgentRecord:
    name = name or pick_agent_name(flag_hint)
    try:
        return default_store().load(name)
    except KeyError:
        msg = f'no agent named {name!r}; see `fleet ls`'
        raise ValueError(msg) from None


def split_agent_args(argv: Sequence[str]) -> tuple[list[str], list[str]]:
    """Everything after the first `--` goes to the agent CLI untouched."""
    if '--' not in argv:
        return list(argv), []
    split_at = list(argv).index('--')
    return list(argv[:split_at]), list(argv[split_at + 1 :])


def replay_command(
    *,
    name: str,
    kind: str,
    repo_dir: Path,
    base: str,
    prompt: str,
    extra_args: Sequence[str],
) -> str:
    parts = ['fleet', 'new', name, '-a', kind, '-C', str(repo_dir)]
    if base:
        parts += ['-b', base]
    if prompt:
        parts += ['-p', prompt]
    if extra_args:
        parts += ['--', *extra_args]
    return shlex.join(parts)


def cmd_new(args: argparse.Namespace, extra_args: list[str]) -> int:
    prompted = False
    key_picked_with_fzf = ''
    name = args.name
    if args.jira is not None:
        ticket = ticket_task(args.jira)
        name = name or jira.agent_name_for(ticket)
        args.prompt = args.prompt or jira.ticket_prompt(ticket)
        key_picked_with_fzf = '' if args.jira else ticket.key
    if not name and not sys.stdin.isatty():
        usage = 'fleet new NAME -p "task"'
        print(f'fleet new: error: missing NAME ({usage})', file=sys.stderr)
        return USAGE_ERROR
    if not name:
        name = prompt_tty('Agent name: ', 'NAME (fleet new NAME)')
        prompted = True
    validate_agent_name(name)
    prompt = args.prompt
    if prompt is None and not sys.stdin.isatty():
        prompt = sys.stdin.read().strip()
    elif prompt is None and prompted:
        prompt = input('Task for the agent (blank = none): ').strip()
    repo_dir = Path(args.repo_dir).resolve()
    record = spawn_agent(
        default_store(),
        default_tmux(),
        SpawnRequest(
            kind=args.agent,
            name=name,
            repo_dir=repo_dir,
            base=args.base or '',
            prompt=prompt or '',
            extra_args=extra_args,
            binary=agent_binary(args.agent),
            hook_path=str(HOOK_PATH),
            session=fleet_session(),
            auto_trust=not args.no_trust,
        ),
    )
    print(f'started {record.kind} agent {record.name!r} in {record.worktree}')
    print(f'  jump in: fleet attach {record.name}   dashboard: fleet')
    if key_picked_with_fzf:
        replay = ['fleet', 'new', name, '--jira', key_picked_with_fzf]
        replay += ['-a', args.agent, '-C', str(repo_dir)]
        print(f'Run again with:\n  {shlex.join(replay)}')
    if prompted:
        print('Run again with:')
        print(
            '  '
            + replay_command(
                name=name,
                kind=args.agent,
                repo_dir=repo_dir,
                base=record.base,
                prompt=prompt or '',
                extra_args=extra_args,
            ),
        )
    return 0


def cmd_ls(args: argparse.Namespace) -> int:
    processes = scan_agent_processes()
    all_rows = dashboard_rows(default_store(), default_tmux(), processes)
    rows = by_urgency(all_rows)
    if args.json:
        print(
            json.dumps(
                [
                    {
                        'name': row.name,
                        'kind': row.kind,
                        'state': row.state.value,
                        'managed': row.record is not None,
                        'where': row.where,
                        'cwd': str(row.cwd),
                        'message': row.message,
                    }
                    for row in rows
                ],
            ),
        )
        return 0
    if not rows:
        print('no agent sessions; start one with: fleet new NAME -p "task"')
        return 0
    for row in rows:
        columns = (
            f'{row.state.value:8} {row.kind:8} {row.name:24} {row.where:24}'
        )
        print(f'{columns} {row.cwd}')
    if not claude_hooks_installed():
        print(
            '\nstates show "unknown" until hooks are on: fleet hooks install',
            file=sys.stderr,
        )
    return 0


def cmd_hooks(args: argparse.Namespace) -> int:
    where = f'fleet hooks in {CLAUDE_SETTINGS}'
    if args.action == 'install':
        changed = install_claude_hooks(CLAUDE_SETTINGS, str(HOOK_PATH))
        print(f'{"installed" if changed else "already installed"}: {where}')
    elif args.action == 'uninstall':
        changed = uninstall_claude_hooks(CLAUDE_SETTINGS)
        print(f'{"removed" if changed else "not installed"}: {where}')
    claude = 'on' if claude_hooks_installed() else 'off (fleet hooks install)'
    copilot = 'on' if COPILOT_HOOK_LINK.exists() else 'off (just symlinks)'
    print(f'claude hooks:  {claude}\ncopilot hooks: {copilot}')
    return 0


def cmd_attach(args: argparse.Namespace) -> int:
    record = find_record(args.name)
    return run_interactive(default_tmux().jump_command(record.window_id))


def cmd_send(args: argparse.Namespace) -> int:
    record = find_record(args.name)
    text = ' '.join(args.text) or prompt_tty(
        'Message: ',
        'TEXT (fleet send NAME TEXT)',
    )
    default_tmux().send_text(record.window_id, text)
    return 0


def cmd_rm(args: argparse.Namespace) -> int:
    record = find_record(args.name)
    kill_agent(
        default_store(),
        default_tmux(),
        record,
        remove_checkout=args.worktree,
        force=args.force,
    )
    kept = '' if args.worktree else f' (worktree kept: {record.worktree})'
    print(
        f'removed agent {record.name!r}; branch {record.branch!r} kept{kept}',
    )
    return 0


def cmd_cockpit(_args: argparse.Namespace) -> int:
    tmux = default_tmux()
    window_id = ensure_dashboard(
        tmux,
        fleet_session(),
        [str(LAUNCHER_PATH)],
        Path.home(),
    )
    return run_interactive(tmux.jump_command(window_id))


def cmd_radar(args: argparse.Namespace) -> int:
    kind = review_agent_kind(args.agent)
    cache = radar.ReviewCache(default_state_dir() / 'reviews')
    prs = radar.fetch_review_requests()
    if args.review:
        for pr in prs:
            if cache.get(pr) is None:
                print(
                    f'reviewing {pr.repo}#{pr.number} with {kind}...',
                    file=sys.stderr,
                )
                fresh = radar.run_review(
                    pr,
                    kind,
                    agent_binary(kind),
                    os.environ.get('FLEET_REVIEW_MODEL', ''),
                )
                cache.put(pr, fresh)
    now = datetime.now(UTC)
    ranked = []
    for pr in prs:
        cached = cache.get(pr)
        score = radar.score_pull_request(
            pr,
            now,
            cached.risk if cached else '',
        )
        ranked.append((score, pr, cached))
    ranked.sort(key=lambda row: row[0].score, reverse=True)
    if args.json:
        print(
            json.dumps(
                [
                    {
                        'score': score.score,
                        'quick': score.quick,
                        'reasons': score.reasons,
                        'repo': pr.repo,
                        'number': pr.number,
                        'title': pr.title,
                        'url': pr.url,
                        'summary': review.summary if review else '',
                        'review_path': str(cache.path(pr)) if review else '',
                    }
                    for score, pr, review in ranked
                ],
            ),
        )
        return 0
    if not ranked:
        print('no open review requests 🎉')
        return 0
    for score, pr, review in ranked:
        quick = '⚡' if score.quick else ' '
        print(
            f'{score.score:3} {quick} {pr.repo}#{pr.number}  {pr.title[:60]}',
        )
        print(f'        {", ".join(score.reasons) or "-"}')
        if review and review.summary:
            print(f'        {review.summary}')
    if not args.review:
        print('\npre-review the rest with: fleet radar --review')
    return 0


def work_json(items: WorkItems, errors: list[str]) -> str:
    return json.dumps(
        {
            'org_repos': [
                {'repo': r.name_with_owner, 'url': r.url}
                for r in items.org_repos
            ],
            'tickets': [
                {
                    'key': t.key,
                    'summary': t.summary,
                    'status': t.status,
                    'url': t.url,
                }
                for t in items.tickets
            ],
            'alarms': [
                {
                    'profile': result.profile.label,
                    'needs_login': result.needs_login,
                    'alarms': [
                        {
                            'name': a.name,
                            'reason': a.reason,
                            'since': a.updated,
                        }
                        for a in result.alarms
                    ],
                }
                for result in items.alarms
            ],
            'log_groups': [
                {'profile': g.profile.label, 'group': g.name}
                for g in items.log_groups
            ],
            'errors': errors,
        },
    )


def print_work(items: WorkItems) -> None:
    for result in items.alarms:
        if result.needs_login:
            command = shlex.join(aws.sso_login_command(result.profile))
            print(f'🔑 {result.profile.label}: login expired, run: {command}')
        for alarm in result.alarms:
            print(f'🚨 {alarm.name} ({result.profile.label})  {alarm.reason}')
        if not result.alarms and not result.needs_login and not result.error:
            print(f'✓ {result.profile.label}: no alarms firing')
    for ticket in items.tickets:
        print(f'🎫 {ticket.key:<12} {ticket.status:<14} {ticket.summary[:60]}')
    if items.org_repos:
        print(f'🌐 {len(items.org_repos)} repos in the configured GitHub orgs')
    for group in items.log_groups:
        print(f'📜 {group.name} ({group.profile.label})')


def cmd_work(args: argparse.Namespace) -> int:
    if args.status:
        print('\n'.join(integration_status(os.environ)))
        return 0
    items, errors = load_work_items(
        os.environ,
        default_state_dir(),
        live_fetchers(),
    )
    if args.json:
        print(work_json(items, errors))
    else:
        print_work(items)
    for error in errors:
        print(f'fleet: {error}', file=sys.stderr)
    return 1 if errors else 0


def pick_ticket(tickets: Sequence[jira.Ticket]) -> jira.Ticket:
    if not tickets:
        msg = 'no open Jira tickets assigned to you (see FLEET_JIRA_JQL)'
        raise ValueError(msg)
    if not sys.stdin.isatty() or shutil.which('fzf') is None:
        keys = ', '.join(ticket.key for ticket in tickets)
        msg = f'missing KEY for --jira; your tickets: {keys}'
        raise ValueError(msg)
    lines = [f'{t.key}\t{t.status}\t{t.summary}' for t in tickets]
    picked = subprocess.run(
        ['fzf', '--prompt', 'ticket> ', '--height', '40%', '--reverse'],  # noqa: S607
        input='\n'.join(lines),
        stdout=subprocess.PIPE,
        text=True,
        check=False,
    ).stdout.partition('\t')[0]
    for ticket in tickets:
        if ticket.key == picked:
            return ticket
    msg = 'no ticket picked'
    raise ValueError(msg)


def ticket_task(key: str) -> jira.Ticket:
    config = jira.jira_config()
    if config is None:
        msg = '--jira needs FLEET_JIRA_URL and a token (see docs/fleet.md)'
        raise ValueError(msg)
    if not key:
        return pick_ticket(jira.fetch_assigned(config))
    return jira.fetch_ticket(config, jira.validate_ticket_key(key))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog='fleet',
        description=(
            'Run parallel Claude Code / Copilot agents, each in its own git '
            'worktree and tmux window, and triage review requests. '
            'Bare `fleet` opens the dashboard.'
        ),
    )
    parser.add_argument(
        '--version',
        action='version',
        version=f'fleet {VERSION}',
    )
    sub = parser.add_subparsers(dest='command')

    new = sub.add_parser(
        'new',
        help='start an agent in a new worktree',
        description=(
            'Start an agent. Args after `--` go to the agent CLI. '
            'The task is read from stdin when piped.'
        ),
    )
    new.add_argument(
        'name',
        nargs='?',
        metavar='NAME',
        help='agent and branch name',
    )
    new.add_argument(
        '-a',
        '--agent',
        choices=AGENT_KINDS,
        default=default_agent_kind(),
    )
    new.add_argument('-p', '--prompt', help='first task for the agent')
    new.add_argument(
        '--jira',
        nargs='?',
        const='',
        metavar='KEY',
        help=(
            'take the task from a Jira ticket; no KEY = pick from yours '
            '(NAME defaults to the key plus its summary)'
        ),
    )
    new.add_argument(
        '-C',
        '--repo-dir',
        default='.',
        help='repo to branch from (default: .)',
    )
    new.add_argument(
        '-b',
        '--base',
        help='base ref (default: the current branch)',
    )
    new.add_argument(
        '--no-trust',
        action='store_true',
        help=(
            "leave the agent's folder-trust dialog to you (by default fleet "
            'answers it when you already trust the source repo)'
        ),
    )

    ls = sub.add_parser('ls', help='list agents and their state')
    ls.add_argument('--json', action='store_true')

    attach = sub.add_parser('attach', help="jump to an agent's tmux window")
    attach.add_argument('name', nargs='?', metavar='NAME')

    send = sub.add_parser('send', help='type a message into an agent')
    send.add_argument('name', nargs='?', metavar='NAME')
    send.add_argument('text', nargs='*', metavar='TEXT')

    rm = sub.add_parser('rm', help='stop an agent (branch is always kept)')
    rm.add_argument('name', nargs='?', metavar='NAME')
    rm.add_argument(
        '--worktree',
        action='store_true',
        help='also remove its worktree',
    )
    rm.add_argument(
        '--force',
        action='store_true',
        help='remove even with uncommitted changes',
    )

    hooks = sub.add_parser(
        'hooks',
        help='global agent hooks, so the dashboard sees every session',
        description=(
            'Claude: merges fleet-hook.sh into ~/.claude/settings.json '
            '(one-time backup kept). Copilot: install/symlinks.sh links its '
            'hook file.'
        ),
    )
    hooks.add_argument(
        'action',
        nargs='?',
        choices=('status', 'install', 'uninstall'),
        default='status',
    )

    sub.add_parser(
        'cockpit',
        help='open the dashboard in the fleet tmux session (Alt+W runs this)',
    )

    radar_parser = sub.add_parser(
        'radar',
        help='rank PRs waiting on your review',
    )
    radar_parser.add_argument(
        '--review',
        action='store_true',
        help='pre-review PRs that have no cached review',
    )
    radar_parser.add_argument(
        '-a',
        '--agent',
        choices=AGENT_KINDS,
        help='reviewer CLI',
    )
    radar_parser.add_argument('--json', action='store_true')

    work = sub.add_parser(
        'work',
        help='firing alarms, your Jira tickets and org repos',
        description=(
            'Fetch every configured work integration (FLEET_GITHUB_ORGS, '
            'FLEET_JIRA_URL, FLEET_AWS_PROFILES). Exits 1 if any source fails.'
        ),
    )
    work.add_argument(
        '--status',
        action='store_true',
        help='show what is configured, without fetching',
    )
    work.add_argument('--json', action='store_true')
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    fleet_args, extra_args = split_agent_args(
        sys.argv[1:] if argv is None else argv,
    )
    parser = build_parser()
    args = parser.parse_args(fleet_args)
    if args.command is None:
        if sys.stdin.isatty() and sys.stdout.isatty():
            from fleet.tui import run_dashboard

            return run_dashboard()
        parser.print_help()
        return 0
    handlers = {
        'ls': cmd_ls,
        'attach': cmd_attach,
        'send': cmd_send,
        'rm': cmd_rm,
        'radar': cmd_radar,
        'work': cmd_work,
        'cockpit': cmd_cockpit,
        'hooks': cmd_hooks,
    }
    try:
        if args.command == 'new':
            return cmd_new(args, extra_args)
        return handlers[args.command](args)
    except (ValueError, FileExistsError) as error:
        print(f'fleet: error: {error}', file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as error:
        stderr = error.stderr if isinstance(error.stderr, str) else ''
        command = shlex.join(map(str, error.cmd))
        print(
            f'fleet: error: {command} failed: {stderr.strip()}',
            file=sys.stderr,
        )
        return 1
