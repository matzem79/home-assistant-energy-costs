"""Recorder boundary and persistence tests without a running HA instance."""
import ast
import asyncio
from datetime import date, datetime, timedelta, timezone
import logging
from pathlib import Path
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from test_ledger import Ledger, module as ledger_module
from test_history import reconstruct

source = Path(__file__).resolve().parents[1] / 'custom_components/energy_costs/runtime.py'
namespace = dict(date=date, timedelta=timedelta, Ledger=Ledger, energy_value=ledger_module.energy_value,
                 reconstruct=reconstruct, callback=lambda f: f, DOMAIN='energy_costs',
                 _LOGGER=logging.getLogger('test_runtime'))
exec(compile(ast.Module(body=[n for n in ast.parse(source.read_text()).body if isinstance(n, ast.ClassDef)],
                        type_ignores=[]), str(source), 'exec'), namespace)
Runtime = namespace['Runtime']


class RuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.now = datetime(2026, 11, 1, 12, 30, tzinfo=timezone.utc)
        self.begin = datetime(2026, 10, 25, 23, tzinfo=timezone.utc).timestamp()
        end = self.now.replace(minute=0).timestamp()
        self.rows = [dict(start=t - 3600, end=t, sum=i, state=5000+i)
                     for i, t in enumerate(range(int(self.begin), int(end)+1, 3600))]
        self.recorder = SimpleNamespace(async_add_executor_job=AsyncMock(return_value={'sensor.import': self.rows}))
        self.recorder.async_db_ready = asyncio.get_running_loop().create_future()
        self.recorder.async_db_ready.set_result(True)
        self.state = SimpleNamespace(state=str(self.rows[-1]['state']+1), attributes={'unit_of_measurement': 'kWh'})
        self.hass = SimpleNamespace(config=SimpleNamespace(time_zone='Europe/Berlin'),
                                    states=SimpleNamespace(get=lambda _: self.state))
        self.entry = SimpleNamespace(data=dict(import_entity='sensor.import', import_billing_start='2026-10-26',
                                              import_history=True), options={}, entry_id='test')
        self.saved = None
        self.store = SimpleNamespace(async_load=AsyncMock(side_effect=lambda: self.saved), async_save=AsyncMock())
        namespace['Store'] = lambda *a: self.store
        namespace['dt_util'] = SimpleNamespace(utcnow=lambda: self.now,
                                               utc_from_timestamp=lambda t: datetime.fromtimestamp(t, timezone.utc))
        recorder_module = ModuleType('homeassistant.components.recorder')
        recorder_module.get_instance = lambda hass: self.recorder
        statistics_module = ModuleType('homeassistant.components.recorder.statistics')
        statistics_module.statistics_during_period = object()
        self.patcher = patch.dict('sys.modules', {
            'homeassistant': ModuleType('homeassistant'),
            'homeassistant.components': ModuleType('homeassistant.components'),
            'homeassistant.components.recorder': recorder_module,
            'homeassistant.components.recorder.statistics': statistics_module})
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    async def test_reload_does_not_import_or_count_again(self):
        runtime = Runtime(self.hass, self.entry)
        await runtime.load()
        energy = sum(b['import'] for b in runtime.ledger.energy.values())
        self.saved = runtime.snapshot()
        restored = Runtime(self.hass, self.entry)
        await restored.load()
        self.assertEqual(self.recorder.async_add_executor_job.await_count, 1)
        self.assertEqual(sum(b['import'] for b in restored.ledger.energy.values()), energy)
        restored.ledger.observe('import', float(self.state.state)+2, self.now.timestamp()+60)
        self.assertEqual(sum(b['import'] for b in restored.ledger.energy.values()), energy+2)
        args = self.recorder.async_add_executor_job.call_args.args
        self.assertEqual(args[-2:], ({'energy': 'kWh'}, {'sum', 'state'}))

    async def test_query_looks_back_a_month_for_sparse_boundary(self):
        runtime = Runtime(self.hass, self.entry)
        await runtime.load()
        query_start = self.recorder.async_add_executor_job.call_args.args[2]
        self.assertEqual(query_start.timestamp(), self.begin - 31 * 86400)

    async def test_old_import_is_rebuilt_once_after_fix(self):
        runtime = Runtime(self.hass, self.entry)
        await runtime.load()
        self.saved = runtime.snapshot()
        self.saved['ledger']['history']['import'].pop('version')
        restored = Runtime(self.hass, self.entry)
        await restored.load()
        self.assertEqual(self.recorder.async_add_executor_job.await_count, 2)
        self.assertEqual(restored.ledger.history['import']['version'], 2)
        self.saved = restored.snapshot()
        await Runtime(self.hass, self.entry).load()
        self.assertEqual(self.recorder.async_add_executor_job.await_count, 2)

    async def test_replacement_preserves_other_direction(self):
        runtime = Runtime(self.hass, self.entry)
        runtime.ledger.energy = {'2026-10-26': {'import': 999, 'export': 42}}
        await runtime.import_history()
        self.assertEqual(runtime.ledger.energy['2026-10-26']['export'], 42)
        self.assertEqual(sum(b['import'] for b in runtime.ledger.energy.values()), len(self.rows))
        self.assertEqual(runtime.ledger.tracking_since('import'), self.begin)

    async def test_no_history_preserves_live_data_and_retries(self):
        self.recorder.async_add_executor_job.return_value = {}
        runtime = Runtime(self.hass, self.entry)
        runtime.ledger.energy = {'2026-11-01': {'import': 5, 'export': 2}}
        with self.assertLogs('test_runtime', level='WARNING'):
            await runtime.import_history()
        self.assertEqual(runtime.ledger.energy['2026-11-01']['import'], 5)
        self.assertFalse(runtime.ledger.history_complete('import'))
        self.recorder.async_add_executor_job.return_value = {'sensor.import': self.rows}
        await runtime.import_history()
        self.assertTrue(runtime.ledger.history_complete('import'))

    async def test_query_failure_keeps_live_accounting(self):
        self.recorder.async_add_executor_job.side_effect = RuntimeError('database unavailable')
        runtime = Runtime(self.hass, self.entry)
        runtime.ledger.observe('import', 100, self.begin)
        with self.assertLogs('test_runtime', level='ERROR'):
            await runtime.import_history()
        runtime.ledger.observe('import', 102, self.begin+60)
        self.assertEqual(runtime.ledger.energy['2026-10-26']['import'], 2)
        self.assertEqual(runtime.ledger.history['import']['status'], 'error')
