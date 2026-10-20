from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

S = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(S))


def load(name):
    spec = importlib.util.spec_from_file_location(name, S / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


pre = load('preflight')
dry = load('dry_run')
log = load('drag_log')

PHONE = {'ProductType': 'iPhone17,2', 'ProductVersion': '27.0.1', 'BuildVersion': '24A446'}


def facts(**changes):
    base = {'macos': '26.6.2', 'arch': 'arm64', 't2': None, 'python': (3, 13, 0), 'mirroring_app': True,
            'swiftc': True, 'ffmpeg': True, 'free_gb': 100.0, 'pmd3': '11.36.0', 'pmd3_requires_python': '>=3.9',
            'phones': [PHONE], 'usb_speed': '480 Mb/s', 'accessibility': None}
    base.update(changes)
    return base


def status(checks, name):
    return next(c['status'] for c in checks if c['name'] == name)


class PreflightTests(unittest.TestCase):
    def test_versions_compare_by_number_not_text(self):
        self.assertTrue(pre.meets(pre.parse_version('15.0'), (15, 0)))
        self.assertTrue(pre.meets(pre.parse_version('26.6.2'), (15, 0)))
        self.assertFalse(pre.meets(pre.parse_version('14.7.1'), (15, 0)))
        self.assertFalse(pre.meets(pre.parse_version('9'), (18, 0)))
        self.assertFalse(pre.meets(None, (15, 0)))

    def test_good_setup_passes_and_warns_about_slow_usb(self):
        checks = pre.evaluate(facts())
        self.assertEqual(status(checks, 'macOS'), 'pass')
        self.assertEqual(status(checks, 'USB speed'), 'warn')
        ready = pre.readiness(checks)
        self.assertTrue(ready['can_read_and_plan'] and ready['can_apply_with_mirroring'])
        self.assertFalse(ready['changes_made'])

    def test_old_macos_blocks_mirroring_but_not_reading(self):
        ready = pre.readiness(pre.evaluate(facts(macos='14.7')))
        self.assertTrue(ready['can_read_and_plan'])
        self.assertFalse(ready['can_apply_with_mirroring'])

    def test_old_ios_blocks_mirroring_and_has_no_touch_route(self):
        checks = pre.evaluate(facts(phones=[dict(PHONE, ProductVersion='17.5')]))
        self.assertEqual(status(checks, 'iOS for Mirroring'), 'fail')
        self.assertIn('not available', next(c['detail'] for c in checks if c['name'].startswith('Touch')))

    def test_intel_without_t2_fails_and_unknown_warns(self):
        self.assertEqual(status(pre.evaluate(facts(arch='x86_64', t2=False)), 'Mac chip'), 'fail')
        self.assertEqual(status(pre.evaluate(facts(arch='x86_64', t2=None)), 'Mac chip'), 'warn')

    def test_missing_tool_and_phone_counts(self):
        checks = pre.evaluate(facts(pmd3=None, phones=None))
        self.assertEqual(status(checks, 'pymobiledevice3'), 'fail')
        self.assertEqual(status(checks, 'iPhone'), 'skip')
        self.assertEqual(status(pre.evaluate(facts(phones=[])), 'iPhone'), 'fail')
        self.assertEqual(status(pre.evaluate(facts(phones=[PHONE, PHONE])), 'iPhone'), 'fail')

    def test_untested_pmd3_version_warns_and_old_python_fails(self):
        self.assertEqual(status(pre.evaluate(facts(pmd3='12.0.0')), 'pymobiledevice3'), 'warn')
        self.assertEqual(status(pre.evaluate(facts(python=(3, 8, 0))), 'Python'), 'fail')

    def test_report_never_carries_serials(self):
        text = json.dumps(pre.evaluate(facts()))
        self.assertNotIn('UniqueDeviceID', text)
        self.assertNotIn('Serial', text)


def state():
    folder = {'listType': 'folder', 'displayName': 'Games', 'iconLists': [['g.one', 'g.two', 'g.three']]}
    widget = {'iconType': 'custom', 'gridSize': 'medium', 'displayIdentifier': 'w'}
    full = [{'displayIdentifier': f'app.{n}'} for n in range(12)]
    return [[{'displayIdentifier': 'dock.a'}], [widget], full, [folder]]


class DryRunTests(unittest.TestCase):
    def test_describes_pages_folders_and_widgets(self):
        found = dry.describe(state())
        self.assertEqual(found['home_screen_pages'], 3)
        self.assertEqual(found['dock_items'], 1)
        self.assertEqual(found['pages'][0]['widgets'], 1)
        self.assertFalse(found['pages'][0]['sparse'])
        self.assertTrue(found['pages'][2]['sparse'])
        self.assertEqual(found['folders'], [{'page': 3, 'name': 'Games', 'apps': 3}])
        self.assertIn('Not visible', found['gaps'])

    def test_plan_checked_and_time_unmeasured_without_log(self):
        before = [[{'displayIdentifier': 'dock'}],
                  [{'displayIdentifier': 'a'}, {'displayIdentifier': 'b'}, {'displayIdentifier': 'c'}]]
        plan = {'replace_pages': [1, 2], 'pages': [{'title': 'One', 'slots': ['a', None, 'b', 'c']}]}
        result = dry.report(before, plan)
        self.assertFalse(result['changes_made'])
        self.assertTrue(result['plan']['valid'])
        self.assertEqual(result['plan']['gap_restoration_drags'], 2)
        self.assertEqual(result['plan']['time']['estimate'], 'unmeasured')

    def test_plan_that_drops_an_icon_is_rejected(self):
        before = [[], [{'displayIdentifier': 'a'}, {'displayIdentifier': 'b'}]]
        plan = {'replace_pages': [1, 2], 'pages': [{'title': 'One', 'slots': ['a', None, None, None]}]}
        result = dry.report(before, plan)
        self.assertFalse(result['plan']['valid'])
        self.assertNotIn('gap_restoration_drags', result['plan'])

    def test_time_comes_from_the_log_when_there_is_one(self):
        before = [[], [{'displayIdentifier': 'a'}, {'displayIdentifier': 'b'}]]
        plan = {'replace_pages': [1, 2], 'pages': [{'title': 'One', 'slots': [None, 'a', None, 'b']}]}
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        entries = [{'at': (start + timedelta(seconds=30 * n)).isoformat(), 'drag_seconds': 5, 'ok': True} for n in range(4)]
        result = dry.report(before, plan, entries)
        self.assertEqual(result['plan']['time']['moves'], 2)
        self.assertEqual(result['plan']['time']['minutes_median'], 1.0)


class TimingTests(unittest.TestCase):
    def entries(self, gaps):
        moment = datetime(2026, 1, 1, tzinfo=timezone.utc)
        found = [{'at': moment.isoformat(), 'drag_seconds': 4.0, 'ok': True}]
        for gap in gaps:
            moment += timedelta(seconds=gap)
            found.append({'at': moment.isoformat(), 'drag_seconds': 4.0, 'ok': True})
        return found

    def test_gaps_over_the_threshold_are_pauses_not_averages(self):
        summary = log.summarize(self.entries([20, 30, 40, 4000]))
        self.assertEqual(summary['pauses_over_threshold'], 1)
        self.assertEqual(summary['seconds_between_moves']['median'], 30)
        self.assertEqual(summary['seconds_between_moves']['samples'], 3)

    def test_failed_moves_are_counted_but_not_timed(self):
        found = self.entries([20, 20])
        found[1]['ok'] = False
        summary = log.summarize(found)
        self.assertEqual(summary['failed_moves'], 1)
        self.assertEqual(summary['drag_seconds']['samples'], 2)

    def test_estimate_uses_checking_time_when_there_are_enough_samples(self):
        estimate = log.estimate(log.summarize(self.entries([30, 30, 30, 30])), 120)
        self.assertEqual(estimate['minutes_median'], 60.0)
        self.assertIn('checking', estimate['basis'])

    def test_estimate_falls_back_to_drag_time_and_says_it_is_low(self):
        estimate = log.estimate(log.summarize(self.entries([30])), 60)
        self.assertEqual(estimate['minutes_median'], 4.0)
        self.assertIn('higher', estimate['basis'])

    def test_estimate_is_unmeasured_without_data(self):
        self.assertEqual(log.estimate(log.summarize([]), 10)['estimate'], 'unmeasured')

    def test_add_and_load_round_trip(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'moves.jsonl'
            log.add_entry(path, 2.5, True, page=3, label='test')
            log.add_entry(path, 1.0, False)
            found = log.load(path)
            self.assertEqual([e['ok'] for e in found], [True, False])
            self.assertEqual(found[0]['page'], 3)
            self.assertEqual(log.load(Path(temp) / 'missing.jsonl'), [])


    def test_run_times_a_helper_and_passes_its_exit_code_on(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'moves.jsonl'
            script = str(S / 'drag_log.py')
            good = subprocess.run([sys.executable, '-B', script, 'run', '--log', str(path), '--page', '2', '--',
                                   sys.executable, '-c', 'pass'], capture_output=True, text=True)
            bad = subprocess.run([sys.executable, '-B', script, 'run', '--log', str(path), '--',
                                  sys.executable, '-c', 'raise SystemExit(4)'], capture_output=True, text=True)
            self.assertEqual((good.returncode, bad.returncode), (0, 4))
            found = log.load(path)
            self.assertEqual([e['ok'] for e in found], [True, False])
            self.assertEqual(found[0]['page'], 2)


class SafetyTests(unittest.TestCase):
    def test_no_script_can_write_the_layout(self):
        forbidden = ('set_icon_state(', 'reload_icon_state', 'setIconState', 'shell=True', 'pip install', 'rm -rf')
        for script in S.glob('*.py'):
            text = script.read_text()
            for word in forbidden:
                self.assertNotIn(word, text, f'{script.name} contains {word}')


if __name__ == '__main__':
    unittest.main()
