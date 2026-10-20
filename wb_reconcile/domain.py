"""Нормализованные данные и сравнение без привязки к API источников."""

from calendar import monthrange
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, localcontext


@dataclass(frozen=True)
class Period:
    mode: str
    start: date
    end: date

    @property
    def days(self) -> tuple[date, ...]:
        return tuple(self.start + timedelta(days=i) for i in range((self.end - self.start).days + 1))


def period(mode: str, start: str, end: str) -> Period:
    first, last = date.fromisoformat(start), date.fromisoformat(end)
    if first.isoformat() != start or last.isoformat() != end:
        raise ValueError('Даты должны иметь формат YYYY-MM-DD')
    count = (last - first).days + 1
    valid = {
        'daily': count in (1, 7),
        'weekly': count == 7,
        'monthly': first.day == 1 and first.year == last.year and first.month == last.month
        and last.day == monthrange(first.year, first.month)[1],
    }
    if not valid.get(mode, False):
        raise ValueError('daily: один или семь дней; weekly: семь дней; monthly: полный календарный месяц')
    return Period(mode, first, last)


@dataclass(frozen=True, order=True)
class Key:
    bucket: str
    metric: str
    organization: str = 'demo-org'
    cabinet: str = 'demo-cabinet'
    segment: str = 'ФЛ'
    currency: str = 'RUB'
    unit: str = 'RUB'


@dataclass(frozen=True)
class Record:
    key: Key
    value: Decimal
    reference: str

    def __post_init__(self):
        if not isinstance(self.value, Decimal) or not self.value.is_finite():
            raise ValueError('Сумма должна быть конечным Decimal, полученным из строки источника')
        if not self.reference:
            raise ValueError('Нужен идентификатор исходной записи')


@dataclass(frozen=True)
class Snapshot:
    source: str
    records: tuple[Record, ...] = ()
    complete: bool = True
    issue: str = ''
    version: str = ''


@dataclass(frozen=True)
class Comparison:
    key: Key
    left_source: str
    right_source: str
    left: Decimal | None
    right: Decimal | None
    difference: Decimal | None
    status: str
    left_refs: tuple[str, ...]
    right_refs: tuple[str, ...]
    note: str = ''


def exact_sum(values: list[Decimal]) -> Decimal:
    """Не округлять промежуточный итог стандартным контекстом Decimal."""
    if not values:
        return Decimal(0)
    integer_places = max(max(v.adjusted() + 1, 1) for v in values)
    fraction_places = max(max(-v.as_tuple().exponent, 0) for v in values)
    with localcontext() as ctx:
        ctx.prec = max(28, integer_places + fraction_places + len(str(len(values))) + 2)
        return sum(values, Decimal(0))


def compare(left: Snapshot, right: Snapshot, expected: tuple[Key, ...], *, approved: bool) -> tuple[Comparison, ...]:
    groups = []
    duplicates = []
    for snapshot in (left, right):
        grouped = defaultdict(list)
        counts = Counter((r.key, r.reference) for r in snapshot.records)
        duplicates.append({key for (key, _), count in counts.items() if count > 1})
        for row in snapshot.records:
            grouped[row.key].append(row)
        groups.append(grouped)
    results = []
    for key in sorted(set(expected) | set(groups[0]) | set(groups[1])):
        a, b = groups[0].get(key, []), groups[1].get(key, [])
        duplicate = key in duplicates[0] or key in duplicates[1]
        av = exact_sum([r.value for r in a]) if a and key not in duplicates[0] else None
        bv = exact_sum([r.value for r in b]) if b and key not in duplicates[1] else None
        difference = None
        if duplicate:
            status = 'дубликат'
        elif not left.complete or not right.complete:
            status = 'неполные данные'
        elif not approved:
            status = 'не сопоставлено'
        elif av is None or bv is None:
            status = 'нет данных'
        else:
            difference = exact_sum([av, bv.copy_negate()])
            status = 'совпало' if difference == 0 else 'расхождение'
        notes = [s.issue for s in (left, right) if s.issue]
        if not approved:
            notes.append('Правило и знак сравнения не утверждены для реальных данных')
        results.append(Comparison(key, left.source, right.source, av, bv, difference, status,
                                  tuple(r.reference for r in a), tuple(r.reference for r in b), '; '.join(notes)))
    return tuple(results)
