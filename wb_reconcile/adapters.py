"""Граница интеграций. В стартовом проекте сетевые адаптеры не реализованы."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from .catalog import metrics
from .domain import Key, Period, Record, Snapshot


class Adapter(Protocol):
    def fetch(self, selected: Period) -> Snapshot: ...


def expected_keys(selected: Period, *, demo: bool) -> tuple[Key, ...]:
    buckets = [d.isoformat() for d in selected.days] if selected.mode == 'daily' else [
        f'{selected.start.isoformat()}..{selected.end.isoformat()}'
    ]
    dimensions = {} if demo else {'organization': 'не настроено', 'cabinet': 'не настроено',
                                  'segment': 'не настроено', 'currency': 'не утверждено'}
    return tuple(Key(bucket, metric, unit=('шт' if metric == 'units' else 'RUB') if demo else 'не утверждено',
                     **dimensions) for bucket in buckets for metric in metrics(selected.mode))


@dataclass
class DemoAdapter:
    source: str

    def fetch(self, selected: Period) -> Snapshot:
        records = []
        for index, key in enumerate(expected_keys(selected, demo=True)):
            value = Decimal('100') + Decimal(index * 10)
            if self.source == 'cube' and index == 0:
                value += Decimal('1') if key.unit == 'шт' else Decimal('0.10')
            records.append(Record(key, value, f'DEMO:{self.source}:{index + 1}'))
        return Snapshot(self.source, tuple(records), version='demo-v1')


@dataclass
class UnconfiguredAdapter:
    source: str

    def fetch(self, selected: Period) -> Snapshot:
        return Snapshot(self.source, complete=False, version='not-configured',
                        issue=f'{self.source}: реальная интеграция ещё не реализована; требуется утверждённый контракт')
