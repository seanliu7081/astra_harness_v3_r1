#!/usr/bin/env python3
"""Inspect or run the standalone, frozen Astra harness v3 r1."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
CUSTOM_TASKS = {
    't04_can_obstacle': ('libero_10_t4', 'Two mugs to plates with the recorded can obstacle'),
    't08_bottle_obstacle': ('libero_10_t8', 'Two moka pots onto the stove with the recorded bottle obstacle'),
}
ALIASES = {'t04': 't04_can_obstacle', 't08': 't08_bottle_obstacle'}


def task_options(name, episode_index, expected=None):
    from gpt_field.agent_speedup_v2_tasks import resolve_v2_task
    name = ALIASES.get(name, name)
    if name in CUSTOM_TASKS:
        if episode_index != 0:
            raise ValueError('Packaged obstacle scenes contain initial state 0 only.')
        data = ROOT / 'tasks' / name
        known = (data / 'initial_observation.sha256').read_text().strip()
        if expected is not None and expected != known:
            raise ValueError('The packaged obstacle reset hash cannot be overridden.')
        return CUSTOM_TASKS[name][0], [
            '--task-bddl-override', str(data / 'custom_task.bddl'),
            '--initial-state-override', str(data / 'initial_state.npy'),
            '--expected-initial-observation-sha256', known,
        ]
    task = resolve_v2_task(name)
    return task.key, [] if expected is None else ['--expected-initial-observation-sha256', expected]


def build_parser():
    from gpt_field.runtime_paths import DEFAULT_AUTH_STORE
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('command', choices=('inspect', 'run'), nargs='?', default='inspect')
    parser.add_argument('--task', default='t04_can_obstacle')
    parser.add_argument('--list-tasks', action='store_true')
    parser.add_argument('--approved', action='store_true', help='Explicitly launch one full task')
    parser.add_argument('--output', type=Path, help='Fresh output directory; never overwritten')
    parser.add_argument('--episode-index', type=int, choices=range(50), default=0)
    parser.add_argument('--vision', choices=('on-demand', 'off'), default='on-demand')
    parser.add_argument('--sam-checkpoint', type=Path)
    parser.add_argument('--da3-model', type=Path)
    parser.add_argument('--vision-device', default='cuda:0')
    parser.add_argument('--vision-max-age-s', type=float, default=60.)
    parser.add_argument('--gpu', type=int, default=int(os.environ.get('MUJOCO_EGL_DEVICE_ID', '0')),
                        help='Physical EGL GPU index; visibility environment is preserved')
    parser.add_argument('--sim-python', type=Path,
                        default=Path(os.environ.get('ASTRA_HARNESS_SIM_PYTHON', ROOT / '.venv-sim/bin/python')))
    parser.add_argument('--libero-root', type=Path,
                        default=Path(os.environ.get('ASTRA_HARNESS_LIBERO_ROOT', ROOT / 'third_party/LIBERO')))
    parser.add_argument('--robot-xml', type=Path)
    parser.add_argument('--expected-initial-observation-sha256')
    parser.add_argument('--initial-state-override', type=Path)
    parser.add_argument('--task-bddl-override', type=Path)
    parser.add_argument('--store-dir', type=Path, default=DEFAULT_AUTH_STORE)
    parser.add_argument('--profile')
    parser.add_argument('--no-video', action='store_true')
    parser.add_argument('--show-command', action='store_true', help='Print command without executing it')
    return parser


def build_command(args):
    if args.command == 'run' and not args.approved:
        raise ValueError('run requires --approved to explicitly launch one full task.')
    if args.command == 'inspect' and args.approved:
        raise ValueError('--approved is meaningful only with run.')
    task, scene = task_options(args.task, args.episode_index, args.expected_initial_observation_sha256)
    custom = ALIASES.get(args.task, args.task) in CUSTOM_TASKS
    if custom and (args.initial_state_override or args.task_bddl_override):
        raise ValueError('Use an official task name when supplying your own scene overrides.')
    command = [sys.executable, '-u', str(ROOT / 'scripts/evaluate_foundation_vision_harness_V3.py'),
               args.command, '--task', task, '--episode-index', str(args.episode_index),
               '--sim-python', str(args.sim_python.expanduser().resolve()),
               '--libero-root', str(args.libero_root.expanduser().resolve()),
               '--vision', args.vision, '--vision-device', args.vision_device,
               '--vision-max-age-s', str(args.vision_max_age_s), *scene]
    for option in ('sam_checkpoint', 'da3_model', 'robot_xml', 'initial_state_override',
                   'task_bddl_override', 'store_dir'):
        value = getattr(args, option)
        if value is not None:
            command.extend(['--' + option.replace('_', '-'), str(value.expanduser().resolve())])
    if args.profile:
        command.extend(['--profile', args.profile])
    if args.no_video:
        command.append('--no-video')
    if args.command == 'run':
        output = args.output or ROOT / 'runs' / (args.task + '_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
        command.extend(['--approved', '--output', str(output.expanduser().resolve())])
    return command


def main(argv=None):
    os.environ['GPT_FIELD_USER_CHECK_TRANSIT_ACTION_M'] = '0.10'
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.list_tasks:
        from gpt_field.agent_speedup_v2_tasks import list_v2_tasks
        for name, (_, description) in CUSTOM_TASKS.items():
            print(f'{name:30s} {description}')
        for task in list_v2_tasks():
            print(f'{task.key:30s} {task.prompt}')
        return 0
    try:
        command = build_command(args)
    except (ValueError, KeyError, OSError) as exc:
        parser.error(str(exc))
    if args.show_command:
        print(json.dumps({'revision': 'astra_tools_r1', 'command': command}, indent=2))
        return 0
    if args.command == 'run':
        if not args.sim_python.expanduser().is_file() or not (args.libero_root.expanduser() / 'libero').is_dir():
            parser.error('Simulator installation missing. Run ./setup.sh first.')
        if args.output and args.output.expanduser().exists():
            parser.error('Choose a fresh --output directory; existing runs are never overwritten.')
    env = os.environ.copy()
    env.pop('OPENAI_API_KEY', None)
    env.update(PYTHONPATH=str(ROOT / 'src'), PYTHONDONTWRITEBYTECODE='1',
               ASTRA_HARNESS_ROOT=str(ROOT), GPT_FIELD_USER_CHECK_TRANSIT_ACTION_M='0.10',
               MUJOCO_GL=env.get('MUJOCO_GL', 'egl'), MUJOCO_EGL_DEVICE_ID=str(args.gpu),
               LIBERO_CONFIG_PATH=str(ROOT / '.local/libero_config'))
    # Replace the launcher so SIGINT/SIGTERM reaches the original runner directly.
    os.execve(sys.executable, command, env)


if __name__ == '__main__':
    raise SystemExit(main())
