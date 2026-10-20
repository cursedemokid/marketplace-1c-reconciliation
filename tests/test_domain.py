from datetime import date
from decimal import Decimal
import unittest

from wb_reconcile.domain import Key, Record, Snapshot, compare, period


class PeriodTests(unittest.TestCase):
    def test_daily_week_keeps_seven_dates(self):
        self.assertEqual(len(period('daily', '2026-08-03', '2026-08-09').days), 7)

    def test_invalid_periods_are_rejected(self):
        for mode, start, end in [
            ('daily', '2026-08-01', '2026-08-02'),
            ('weekly', '2026-08-01', '2026-08-06'),
            ('monthly', '2026-08-02', '2026-08-31'),
            ('monthly', '2026-08-01', 'DemoPhone'),
            ('daily', '2026-08-02', '2026-08-01'),
            ('unknown', '2026-08-01', '2026-08-01'),
        ]:
            with self.subTest(mode=mode, start=start), self.assertRaises(ValueError):
                period(mode, start, end)

    def test_leap_month(self):
        self.assertEqual(period('monthly', '2028-02-01', '2028-02-29').end, date(2028, 2, 29))


class ComparisonTests(unittest.TestCase):
    def setUp(self):
        self.key = Key('2026-08-01', 'payment')

    def snapshot(self, source, value, reference='line-1', complete=True):
        rows = () if value is None else (Record(self.key, Decimal(value), reference),)
        return Snapshot(source, rows, complete=complete)

    def test_exact_decimal_and_left_minus_right(self):
        left = Snapshot('cube', (Record(self.key, Decimal('0.10'), 'a'), Record(self.key, Decimal('0.20'), 'b')))
        result = compare(left, self.snapshot('wb', '0.29'), (self.key,), approved=True)[0]
        self.assertEqual(result.left, Decimal('0.30'))
        self.assertEqual(result.difference, Decimal('0.01'))
        self.assertEqual(result.status, 'расхождение')
        self.assertEqual(result.left_refs, ('a', 'b'))

    def test_missing_is_not_zero(self):
        result = compare(self.snapshot('cube', None), self.snapshot('wb', '0'), (self.key,), approved=True)[0]
        self.assertIsNone(result.left)
        self.assertIsNone(result.difference)
        self.assertEqual(result.status, 'нет данных')

    def test_incomplete_source_never_matches(self):
        result = compare(self.snapshot('cube', '5', complete=False), self.snapshot('wb', '5'), (self.key,), approved=True)[0]
        self.assertEqual(result.status, 'неполные данные')
        self.assertIsNone(result.difference)

    def test_duplicate_is_not_summed(self):
        row = Record(self.key, Decimal('5'), 'same-line')
        result = compare(Snapshot('cube', (row, row)), self.snapshot('wb', '10'), (self.key,), approved=True)[0]
        self.assertEqual(result.status, 'дубликат')
        self.assertIsNone(result.difference)

    def test_unapproved_mapping_never_matches(self):
        result = compare(self.snapshot('cube', '5'), self.snapshot('wb', '5'), (self.key,), approved=False)[0]
        self.assertEqual(result.status, 'не сопоставлено')
        self.assertIsNone(result.difference)

    def test_different_dimensions_are_not_combined(self):
        other = Key('2026-08-01', 'payment', cabinet='other')
        result = compare(self.snapshot('cube', '5'), Snapshot('wb', (Record(other, Decimal('5'), 'b'),)), (self.key,), approved=True)
        self.assertEqual(len(result), 2)
        self.assertTrue(all(row.status == 'нет данных' for row in result))

    def test_nonfinite_money_is_rejected(self):
        for value in ('NaN', 'Infinity', '-Infinity'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                Record(self.key, Decimal(value), 'bad')


if __name__ == '__main__':
    unittest.main()
