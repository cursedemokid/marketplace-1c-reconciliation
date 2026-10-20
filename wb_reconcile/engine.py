"""Маршрутизация режимов: WB не участвует в недельной сверке."""

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from .adapters import Adapter, expected_keys
from .catalog import SOURCES
from .domain import Comparison, Period, Snapshot, compare


@dataclass(frozen=True)
class Run:
    run_id: str
    created_at: str
    selected: Period
    demo: bool
    snapshots: tuple[Snapshot, ...]
    comparisons: tuple[Comparison, ...]

    @property
    def status(self) -> str:
        if not self.comparisons or any(r.status not in ('совпало', 'расхождение') for r in self.comparisons):
            return 'неполные данные'
        return 'расхождение' if any(r.status == 'расхождение' for r in self.comparisons) else 'совпало'


def execute(selected: Period, adapters: dict[str, Adapter], *, demo: bool = False) -> Run:
    required = SOURCES[selected.mode]
    snapshots = []
    for source in required:
        if source not in adapters:
            raise ValueError(f'Не задан адаптер {source}')
        try:
            snapshot = adapters[source].fetch(selected)
            if snapshot.source != source:
                raise ValueError('Источник не соответствует адаптеру')
        except Exception:
            # Тексты сетевых ошибок могут содержать URL с токеном или пароль.
            snapshot = Snapshot(source, complete=False, issue=f'{source}: ошибка загрузки; проверьте адаптер')
        snapshots.append(snapshot)
    expected = expected_keys(selected, demo=demo)
    pairs = ((0, 1), (0, 2)) if selected.mode == 'monthly' else ((0, 1),)
    comparisons = tuple(row for left, right in pairs
                        for row in compare(snapshots[left], snapshots[right], expected, approved=demo))
    return Run(uuid4().hex, datetime.now(timezone.utc).isoformat(), selected, demo,
               tuple(snapshots), comparisons)
