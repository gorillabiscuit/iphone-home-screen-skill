from contextlib import closing
import hashlib
import importlib.util
import json
from pathlib import Path
import plistlib
import sqlite3
import tempfile
import unittest
from PIL import Image,ImageDraw

S=Path(__file__).resolve().parents[1]/'scripts'
def load(name):
    spec=importlib.util.spec_from_file_location(name,S/(name+'.py'))
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
bp=load('backup_positions');colour=load('classify_icons');cost=load('plan_review');layout=load('layout')

class ResearchTests(unittest.TestCase):
    def setUp(self):
        self.state={'listUniqueIdentifiers':['page1'],'listMetadata':{'page1':{
            'fixedLocations':{'app.a':5,'app.b':10},'fixedLocationsGridRows':6,'fixedLocationsGridColumns':4}},
            'iconLists':[['app.a','app.b']],'buttonBar':[]}
    def raw(self):return plistlib.dumps(self.state,fmt=plistlib.FMT_BINARY)
    def test_no_guess_without_observation(self):
        result=bp.analyse(self.raw());self.assertIsNone(result['index_base']);self.assertEqual(result['pins_found'],2)
    def test_zero_based_evidence(self):
        result=bp.analyse(self.raw(),[{'page_index':0,'identity':'app.a','row':2,'column':2},{'page_index':0,'identity':'app.b','row':3,'column':3}])
        self.assertEqual(result['index_base'],0)
    def test_one_based_evidence(self):
        result=bp.analyse(self.raw(),[{'page_index':0,'identity':'app.a','row':2,'column':1}])
        self.assertEqual(result['index_base'],1)
    def test_contradiction_stays_unknown(self):
        result=bp.analyse(self.raw(),[{'page_index':0,'identity':'app.a','row':2,'column':2},{'page_index':0,'identity':'app.b','row':3,'column':2}])
        self.assertIsNone(result['index_base']);self.assertEqual(result['status'],'contradictory observations')
    def test_usb_array_not_backup(self):
        with self.assertRaises(ValueError):bp.analyse(plistlib.dumps([[]]))
    def test_backup_lookup_and_encryption_guard(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);payload=self.raw()
            (root/'Manifest.plist').write_bytes(plistlib.dumps({'IsEncrypted':False}))
            fid=hashlib.sha1(b'HomeDomain-Library/SpringBoard/IconState.plist').hexdigest()
            with closing(sqlite3.connect(root/'Manifest.db')) as db:
                db.execute('CREATE TABLE Files (fileID TEXT, domain TEXT, relativePath TEXT)')
                db.execute('INSERT INTO Files VALUES (?,?,?)',(fid,'HomeDomain','Library/SpringBoard/IconState.plist'));db.commit()
            (root/fid[:2]).mkdir();(root/fid[:2]/fid).write_bytes(payload)
            self.assertEqual(bp.extract(root),payload)
            (root/'Manifest.plist').write_bytes(plistlib.dumps({'IsEncrypted':True}))
            with self.assertRaises(ValueError):bp.extract(root)
    def test_no_grid_no_fabricated_cells(self):
        del self.state['listMetadata']['page1']['fixedLocationsGridRows']
        self.assertNotIn('candidate_cells',bp.analyse(self.raw())['pages'][0]['pins'][0])
    def test_binary_snapshot(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'snap.plist';layout.save_new(path,[[{'displayIdentifier':'a'}]])
            self.assertTrue(path.read_bytes().startswith(b'bplist00'))
    def test_colour_white_blue(self):
        with tempfile.TemporaryDirectory() as temp:
            im=Image.new('RGBA',(128,128),'white');ImageDraw.Draw(im).ellipse((30,30,98,98),fill='#0066ff')
            path=Path(temp)/'icon.png';im.save(path);result=colour.classify(path)
            self.assertEqual(result['background_bucket'],'white')
            self.assertEqual(result['alternative_bucket'],'blue')
    def test_transparent_not_black_colour(self):
        with tempfile.TemporaryDirectory() as temp:
            im=Image.new('RGBA',(128,128),(0,0,0,0));ImageDraw.Draw(im).rounded_rectangle((0,0,127,127),radius=28,fill='#10bb20')
            path=Path(temp)/'icon.png';im.save(path);result=colour.classify(path)
            self.assertEqual(result['background_bucket'],'green');self.assertFalse(result['neutral'])
    def test_no_opaque_pixels_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'icon.png';Image.new('RGBA',(128,128),(0,0,0,0)).save(path)
            with self.assertRaises(ValueError):colour.classify(path)
    def test_move_cost_leading_vs_trailing(self):
        result=cost.review({'pages':[{'slots':['a','b',None,None]},{'slots':[None,None,'a','b']}]})
        self.assertEqual([p['gap_restoration_drags'] for p in result['pages']],[0,2])

if __name__=='__main__':unittest.main()
