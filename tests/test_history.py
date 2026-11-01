"""Historical statistics, live handover and independent billing periods."""
import ast
import json
from pathlib import Path
import unittest

from test_ledger import Ledger, at, tariff

source = Path(__file__).resolve().parents[1] / 'custom_components/energy_costs/history.py'
namespace = {}
exec(compile(ast.Module(body=[n for n in ast.parse(source.read_text()).body
                             if not isinstance(n, (ast.Import, ast.ImportFrom))], type_ignores=[]),
             str(source), 'exec'), dict(__import__('math').__dict__, Ledger=Ledger), namespace)
reconstruct = namespace['reconstruct']


class HistoryTests(unittest.TestCase):
    def setUp(self):
        self.begin = at('2026-10-26T00:00:00+01:00')
        self.rows = [dict(start=self.begin - 3600, end=self.begin, sum=1000, state=5000),
                     dict(start=self.begin, end=self.begin + 3600, sum=1002, state=5002),
                     dict(start=self.begin + 3600, end=self.begin + 7200, sum=1005, state=5005)]

    def build(self, **kwargs):
        return reconstruct('Europe/Berlin', kwargs.pop('direction', 'import'), kwargs.pop('rows', self.rows),
                           self.begin, kwargs.pop('now', self.begin + 9000), kwargs.pop('current', 5006))

    def test_sum_offset_not_meter_lifetime_and_live_tail_only_once(self):
        ledger = self.build()
        ledger.observe('import', 5006, self.begin + 9060)
        ledger.observe('import', 5007, self.begin + 9120)
        self.assertAlmostEqual(sum(b['import'] for b in ledger.energy.values()), 7)
        self.assertTrue(ledger.history_complete('import'))
        self.assertEqual(ledger.tracking_since('import'), self.begin)

    def test_statistics_resets_use_adjusted_sum(self):
        self.rows[-1]['state'] = 1
        ledger = self.build(current=2)
        self.assertEqual(sum(b['import'] for b in ledger.energy.values()), 6)

    def test_missing_baseline_reports_partial(self):
        ledger = self.build(rows=self.rows[1:])
        self.assertFalse(ledger.history_complete('import'))
        self.assertEqual(ledger.tracking_since('import'), self.begin + 3600)
        self.assertEqual(sum(b['import'] for b in ledger.energy.values()), 4)

    def test_no_statistics_does_not_replace_live_data(self):
        self.assertIsNone(self.build(rows=[]))
        self.assertIsNone(self.build(current=None))

    def test_gap_keeps_known_cumulative_energy_and_decreasing_sum_incomplete(self):
        self.rows[-1].update(start=self.begin + 7200, end=self.begin + 10800)
        ledger = self.build(now=self.begin + 12000)
        self.assertTrue(ledger.history_complete('import'))
        self.assertTrue(ledger.history['import']['distribution_estimated'])
        self.assertEqual(ledger.history['import']['statistics_gaps'], 1)
        self.assertEqual(sum(b['import'] for b in ledger.energy.values()), 6)
        self.rows[-1]['sum'] = 0
        ledger = self.build(now=self.begin + 12000)
        self.assertFalse(ledger.history_complete('import'))
        self.assertGreaterEqual(sum(b['import'] for b in ledger.energy.values()), 0)

    def test_tail_reset_incomplete_and_long_monotonic_tail_estimated(self):
        self.assertFalse(self.build(current=1).history_complete('import'))
        ledger = self.build(now=self.begin + 20000)
        self.assertTrue(ledger.history_complete('import'))
        self.assertTrue(ledger.history['import']['distribution_estimated'])

    def test_requested_start_clips_first_interval(self):
        self.rows[0].update(end=self.begin - 1800)
        ledger = self.build()
        self.assertAlmostEqual(sum(b['import'] for b in ledger.energy.values()), 2 * 3600 / 5400 + 4)
        self.assertNotIn('2026-10-25', ledger.energy)
        self.assertFalse(ledger.history_complete('import'))
        self.assertIn('estimated_start_boundary', ledger.history['import']['incomplete_reasons'])

    def test_april_boundary_spanned_by_multiday_gap(self):
        begin = at('2026-04-01T00:00:00+02:00')
        left = at('2026-03-30T11:00:00+00:00')
        right = at('2026-04-02T08:00:00+00:00')
        end = at('2026-11-01T14:00:00+00:00')
        rows = [dict(start=t-3600, end=t, sum=v-4000, state=v)
                for t, v in [(left, 4735.2156), (right, 4741.7273), (end, 5739.4989)]]
        ledger = reconstruct('Europe/Berlin', 'export', rows, begin, end+1800, 5739.4989)
        expected = (4741.7273-4735.2156) * (right-begin)/(right-left) + 5739.4989-4741.7273
        self.assertAlmostEqual(sum(b['export'] for b in ledger.energy.values()), expected)
        self.assertAlmostEqual(expected, 1000.980263768, places=6)
        self.assertEqual(ledger.tracking_since('export'), begin)
        self.assertEqual(ledger.history['export']['incomplete_reasons'], ['estimated_start_boundary'])
        settings = dict(tariffs=[tariff('2026-04-01')], export_billing_start='2026-04-01')
        result = ledger.settlement('export', end+1800, settings)
        self.assertAlmostEqual(result['actual'], expected * 0.08)
        self.assertIn('estimated_start_boundary', result['incomplete_reasons'])
        self.assertFalse(result['complete'])

    def test_zero_duration_zero_energy_tail_is_complete(self):
        ledger = self.build(now=self.begin+7200, current=5005)
        self.assertTrue(ledger.history_complete('import'))

    def test_unpriced_history_reports_tariff_as_reason(self):
        ledger = self.build()
        settings = dict(tariffs=[tariff('2026-11-01')], import_billing_start='2026-10-26')
        result = ledger.settlement('import', self.begin+9000, settings)
        self.assertFalse(result['complete'])
        self.assertIn('missing_tariff', result['incomplete_reasons'])
        self.assertIn('missing_payment_tariff', result['incomplete_reasons'])

    def test_independent_history_start_persists_and_prices_recalculate(self):
        ledger = self.build()
        ledger.started = self.begin + 9000
        export_begin = at('2026-04-01T00:00:00+02:00')
        ledger.history['export'] = dict(tracking_since=export_begin, complete=True)
        restored = Ledger('Europe/Berlin')
        restored.restore(json.loads(json.dumps(ledger.dump())))
        self.assertEqual(restored.tracking_since('export'), export_begin)
        settings = dict(tariffs=[dict(tariff('2026-04-01', monthly_fee=0), monthly_import_payment=100)],
                        import_billing_start='2026-10-26', export_billing_start='2026-04-01')
        result = restored.settlement('import', self.begin + 9000, settings)
        self.assertTrue(result['complete'])
        self.assertAlmostEqual(result['actual'], 1.8)
        self.assertEqual(result['advances'], 100)
        settings['tariffs'][0]['import_price'] = 0.5
        self.assertAlmostEqual(restored.settlement('import', self.begin + 9000, settings)['actual'], 3)


if __name__ == '__main__':
    unittest.main()
