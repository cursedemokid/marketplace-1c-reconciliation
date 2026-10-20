"""Командный запуск каркаса. Доступ к внешним системам ещё не реализован."""

import argparse
import json
import os
from pathlib import Path
import sys

from .adapters import DemoAdapter, UnconfiguredAdapter
from .catalog import SOURCES
from .domain import period
from .engine import execute
from .excel import write_workbook
from .report import report_sheets


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='Сверка WB, куба и 1С — стартовый проект по ТЗ v2')
    commands = parser.add_subparsers(dest='command', required=True)
    run_parser = commands.add_parser('run', help='Сформировать результат в Excel')
    run_parser.add_argument('--mode', choices=tuple(SOURCES), required=True)
    run_parser.add_argument('--start', required=True, help='YYYY-MM-DD')
    run_parser.add_argument('--end', required=True, help='YYYY-MM-DD')
    run_parser.add_argument('--demo', action='store_true', help='Использовать явно искусственные данные')
    run_parser.add_argument('--output-dir', type=Path, default=Path('reports'))
    args = parser.parse_args(argv)
    try:
        selected = period(args.mode, args.start, args.end)
    except ValueError as error:
        print(f'Неверный период: {error}', file=sys.stderr)
        return 1
    adapter_type = DemoAdapter if args.demo else UnconfiguredAdapter
    adapters = {source: adapter_type(source) for source in SOURCES[args.mode]}
    result = execute(selected, adapters, demo=args.demo)
    stem = f'{args.mode}_{args.start}_{args.end}_{result.run_id}'
    path = args.output_dir / f'{stem}.xlsx'
    log = {
        'run_id': result.run_id, 'created_at_utc': result.created_at, 'demo': result.demo,
        'mode': selected.mode, 'start': selected.start.isoformat(), 'end': selected.end.isoformat(),
        'status': result.status, 'rule_version': 'demo-v1' if result.demo else 'draft-v2',
        'sources': [{'source': s.source, 'complete': s.complete, 'rows': len(s.records),
                     'version': s.version} for s in result.snapshots],
        'comparisons': len(result.comparisons),
    }
    try:
        args.output_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        write_workbook(path, report_sheets(result))
        log_path = args.output_dir / f'{stem}.json'
        with os.fdopen(os.open(log_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w', encoding='utf-8') as stream:
            json.dump(log, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
    except (OSError, ValueError):
        print('Не удалось сохранить результат. Проверьте доступ к каталогу и формат данных.', file=sys.stderr)
        return 1
    label = 'ДЕМОНСТРАЦИЯ' if result.demo else 'ИСТОЧНИКИ НЕ ПОДКЛЮЧЕНЫ'
    print(f'{label} | {result.status}\nExcel: {path.resolve()}\nЖурнал: {log_path.resolve()}')
    return {'совпало': 0, 'расхождение': 2, 'неполные данные': 3}[result.status]
