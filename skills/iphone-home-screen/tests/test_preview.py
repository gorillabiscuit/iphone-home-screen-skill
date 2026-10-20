import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

S = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(S))

try:
    import numpy
    from PIL import Image
    IMAGING = True
except ImportError:
    IMAGING = False


def load(name):
    spec = importlib.util.spec_from_file_location(name, S / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


preview = load('preview')
layout = load('layout')


def app(name, ident=None):
    ident = ident or 'app.' + name.lower()
    return {'displayIdentifier': ident, 'bundleIdentifier': ident, 'displayName': name}


WIDGET = {'iconType': 'custom', 'gridSize': 'medium', 'displayIdentifier': 'widget.one'}
FOLDER = {'listType': 'folder', 'displayName': 'Games', 'iconLists': [[app('G1'), app('G2')]]}
NAMES = ['Zeta', 'Alpha', 'Mike', 'Bravo', 'Echo', 'Delta']


def state():
    loose = [app(n) for n in NAMES]
    return [[app('Dock')], [WIDGET], loose[:3] + [FOLDER], loose[3:]]


def colours():
    """Made-up colour records: hue and lightness decide the order, 'neutral' goes last."""
    return {'app.zeta': {'base_oklch': [0.6, 0.2, 250.0], 'neutral': False},   # blue
            'app.alpha': {'base_oklch': [0.6, 0.2, 30.0], 'neutral': False},   # red
            'app.mike': {'base_oklch': [0.9, 0.0, 0.0], 'neutral': True},       # white
            'app.bravo': {'base_oklch': [0.7, 0.2, 140.0], 'neutral': False},  # green
            'app.echo': {'base_oklch': [0.2, 0.0, 0.0], 'neutral': True},       # black
            'app.delta': {'base_oklch': [0.7, 0.2, 80.0], 'neutral': False}}   # yellow


def plan_names(plan, state_):
    start, end = plan['replace_pages']
    by_key = {preview.key_of(i): preview.label(i) for p in state_[start:end] for i in layout.entries(p)}
    return [[by_key.get(k) for k in page['slots']] for page in plan['pages']]


class StrategyTests(unittest.TestCase):
    def test_widget_pages_are_left_out_of_the_range(self):
        self.assertEqual(preview.movable_range(state()), (2, 4))

    def test_colour_runs_red_to_blue_then_greys_then_folders_last(self):
        plan = preview.make_plan(state(), 'colour', colours(), 4, 6)
        names = [n for page in plan_names(plan, state()) for n in page if n]
        self.assertEqual(names, ['Alpha', 'Delta', 'Bravo', 'Zeta', 'Mike', 'Echo', 'Games'][:-1] + ['Games'])
        self.assertEqual(plan['replace_pages'], [2, 4])

    def test_alphabetical(self):
        plan = preview.make_plan(state(), 'alphabetical', {}, 4, 6)
        names = [n for page in plan_names(plan, state()) for n in page if n]
        self.assertEqual(names[:6], sorted(NAMES))
        self.assertEqual(names[-1], 'Games')

    def test_favourites_take_the_bottom_cells_of_page_one_and_leave_the_top_empty(self):
        many = [app(f'App{n:02}') for n in range(30)]
        big = [[app('Dock')], many]
        plan = preview.make_plan(big, 'favourites', {}, 4, 6, favourites=['App03', 'app.app07'], then='alphabetical')
        first = plan_names(plan, big)[0]
        self.assertEqual(len(first), 24)
        self.assertEqual(first[-2:], ['App03', 'App07'])
        self.assertEqual(first.count(None), 22)
        self.assertEqual(plan['pages'][0]['title'], 'Favourites')
        self.assertNotIn('App03', [n for page in plan_names(plan, big)[1:] for n in page])
        self.assertEqual(plan_names(plan, big)[1][0], 'App00')

    def test_favourites_can_fill_the_rest_of_page_one(self):
        many = [app(f'App{n:02}') for n in range(30)]
        big = [[app('Dock')], many]
        plan = preview.make_plan(big, 'favourites', {}, 4, 6, favourites=['App03', 'App07'], then='alphabetical', fill_page_one=True)
        first = plan_names(plan, big)[0]
        self.assertEqual((first[-2:], first.count(None)), (['App03', 'App07'], 0))

    def test_favourites_then_groups_gives_group_pages_after_page_one(self):
        many = [app(f'App{n:02}') for n in range(30)]
        big = [[app('Dock')], many]
        groups = {'Money': [f'App{n:02}' for n in range(10, 22)]}
        plan = preview.make_plan(big, 'favourites', {}, 4, 6, favourites=['App01'], groups=groups, then='groups')
        titles = [p['title'] for p in plan['pages']]
        self.assertEqual(titles[:2], ['Favourites', 'Money'])

    def test_favourites_that_match_nothing_are_refused(self):
        with self.assertRaises(ValueError):
            preview.make_plan(state(), 'favourites', {}, 4, 6, favourites=['No such app'])

    def test_groups_keep_names_and_join_small_groups(self):
        groups = {'Early': ['Alpha', 'Bravo'], 'Late': ['Zeta']}
        plan = preview.make_plan(state(), 'groups', colours(), 4, 6, groups=groups)
        titles = [p['title'] for p in plan['pages']]
        self.assertEqual(titles[0], 'Early + Late + Other')
        self.assertEqual(titles[-1], 'Folders')
        big = {'Big': [f'App{n:02}' for n in range(14)], 'Small': ['App20']}
        many = [[app('Dock')], [app(f'App{n:02}') for n in range(30)]]
        titles = [p['title'] for p in preview.make_plan(many, 'groups', {}, 4, 6, groups=big)['pages']]
        self.assertEqual(titles[:2], ['Big', 'Small + Other'])

    def test_every_strategy_keeps_every_icon_once(self):
        for strategy in preview.STRATEGIES:
            plan = preview.make_plan(state(), strategy, colours(), 4, 6, groups={'One': ['Alpha']}, favourites=['Echo'], then='groups')
            keys = [k for page in plan['pages'] for k in page['slots'] if k]
            self.assertEqual(len(keys), len(set(keys)), strategy)
            self.assertEqual(len(keys), len(NAMES) + 1, strategy)
            layout.build(state(), plan)

    def test_unknown_strategy_is_refused(self):
        with self.assertRaises(ValueError):
            preview.make_plan(state(), 'nonsense', {}, 4, 6)

    def test_a_user_plan_with_gaps_is_drawn_cell_by_cell(self):
        plan = {'replace_pages': [2, 4], 'pages': [
            {'title': 'Mine', 'slots': [None, 'app.alpha', None, 'app.zeta', 'app.mike', 'app.bravo', 'app.echo', 'app.delta']},
            {'title': 'Folders', 'slots': ['folder:Games', None, None, None]}]}
        pages, titles = preview.plan_view(state(), plan, 4, 6)
        mine = next(p for p in pages if len(p) == 6)
        self.assertEqual(sorted((c['col'], c['row']) for c in mine)[0], (0, 1))
        self.assertIn('Mine', titles)

    def test_a_plan_that_loses_an_icon_is_refused(self):
        plan = {'replace_pages': [2, 4], 'pages': [{'title': 'Short', 'slots': ['app.alpha', None, None, None]}]}
        with self.assertRaises(ValueError):
            layout.build(state(), plan)


@unittest.skipUnless(IMAGING, 'needs Pillow and numpy')
class PictureTests(unittest.TestCase):
    def make_icons(self, folder):
        manifest = []
        shades = {'app.zeta': (30, 60, 220), 'app.alpha': (220, 40, 40), 'app.mike': (250, 250, 250),
                  'app.bravo': (40, 180, 70), 'app.echo': (15, 15, 15), 'app.delta': (240, 200, 30)}
        for ident, rgb in shades.items():
            path = Path(folder) / (ident + '.png')
            Image.new('RGBA', (120, 120), rgb + (255,)).save(path)
            manifest.append({'identity': ident, 'label': ident, 'path': str(path)})
        return manifest

    def test_pictures_and_plan_are_written_and_nothing_else_changes(self):
        import plistlib
        with tempfile.TemporaryDirectory() as temp:
            temp = Path(temp)
            (temp / 'before.plist').write_bytes(plistlib.dumps(state(), fmt=plistlib.FMT_BINARY))
            manifest = self.make_icons(temp)
            (temp / 'manifest.json').write_text(json.dumps(manifest))
            before = (temp / 'before.plist').read_bytes()
            done = subprocess.run([sys.executable, '-B', str(S / 'preview.py'), '--snapshot', str(temp / 'before.plist'),
                                   '--manifest', str(temp / 'manifest.json'), '--out', str(temp / 'out')],
                                  capture_output=True, text=True)
            self.assertEqual(done.returncode, 0, done.stderr)
            for name in ('current.png', 'proposed.png', 'plan.json', 'summary.json', 'colours.json'):
                self.assertTrue((temp / 'out' / name).exists(), name)
            summary = json.loads((temp / 'out' / 'summary.json').read_text())
            self.assertFalse(summary['changes_made'])
            self.assertEqual(summary['apps_classified'], 6)
            self.assertEqual((temp / 'before.plist').read_bytes(), before)
            again = subprocess.run([sys.executable, '-B', str(S / 'preview.py'), '--snapshot', str(temp / 'before.plist'),
                                    '--manifest', str(temp / 'manifest.json'), '--out', str(temp / 'out')],
                                   capture_output=True, text=True)
            self.assertNotEqual(again.returncode, 0)

    def test_a_real_classification_orders_red_before_blue_before_white(self):
        with tempfile.TemporaryDirectory() as temp:
            found = preview.classify_all(self.make_icons(temp))
            order = preview.order_colour(['app.zeta', 'app.mike', 'app.alpha', 'app.echo'], found)
            self.assertEqual(order, ['app.alpha', 'app.zeta', 'app.mike', 'app.echo'])


if __name__ == '__main__':
    unittest.main()
