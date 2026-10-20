from decimal import Decimal
import unittest

from wb_reconcile.adapters import DemoAdapter, UnconfiguredAdapter
from wb_reconcile.domain import period
from wb_reconcile.engine import execute


class EngineTests(unittest.TestCase):
    def adapters(self, names):
        return {name: DemoAdapter(name) for name in names}

    def test_daily_seven_independent_days(self):
        run = execute(period('daily', '2026-08-03', '2026-08-09'),
                      self.adapters(('cube', 'wb_reports')), demo=True)
        self.assertEqual(len(run.comparisons), 7)
        self.assertEqual(len({r.key.bucket for r in run.comparisons}), 7)
        self.assertEqual(run.comparisons[0].difference, Decimal('0.10'))
        self.assertEqual({s.source for s in run.snapshots}, {'cube', 'wb_reports'})

    def test_weekly_works_without_any_wb_adapter(self):
        run = execute(period('weekly', '2026-08-03', '2026-08-09'),
                      self.adapters(('cube', 'one_c')), demo=True)
        self.assertEqual(len(run.comparisons), 7)
        self.assertEqual({s.source for s in run.snapshots}, {'cube', 'one_c'})
        quantity = next(r for r in run.comparisons if r.key.metric == 'units')
        self.assertEqual(quantity.key.unit, 'шт')

    def test_monthly_keeps_two_independent_comparisons(self):
        run = execute(period('monthly', '2026-08-01', '2026-08-31'),
                      self.adapters(('wb_documents', 'cube', 'one_c')), demo=True)
        self.assertEqual(len(run.comparisons), 14)
        self.assertEqual({(r.left_source, r.right_source) for r in run.comparisons},
                         {('wb_documents', 'cube'), ('wb_documents', 'one_c')})

    def test_unconfigured_sources_are_incomplete(self):
        run = execute(period('daily', '2026-08-01', '2026-08-01'),
                      {n: UnconfiguredAdapter(n) for n in ('cube', 'wb_reports')})
        self.assertEqual(run.status, 'неполные данные')
        self.assertTrue(all(r.difference is None for r in run.comparisons))
        self.assertFalse(any(s.complete for s in run.snapshots))


if __name__ == '__main__':
    unittest.main()
