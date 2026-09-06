import unittest
from pathlib import Path
from unittest.mock import patch
import project_config as c

class RelativePaths(unittest.TestCase):
    def test_current(self):
        result=c.resolve('kibu1')
        self.assertEqual(result['installation'],c.ROOT.parent)
        self.assertEqual(c.resolve(project=result['project'])['id'],'kibu1')

    def test_two_games_and_relocated_root(self):
        with patch.object(c, 'ROOT', c.ROOT / 'virtual-relocation'):
            temp=c.ROOT
            root=Path(temp)/'系列 工程'
            data={'schema':1,'default_game':'one','games':{
                'one':dict(project='games/one',installation='../游戏 一',adapter='v1',enabled=True),
                'two':dict(project='games/two',installation='../游戏 二',adapter='v2',enabled=True)}}
            with patch.object(c,'ROOT',root),patch.object(c,'read',return_value=data):
                self.assertEqual(c.resolve()['installation'],Path(temp)/'游戏 一')
                self.assertEqual(c.resolve('two')['installation'],Path(temp)/'游戏 二')
                self.assertEqual(c.resolve('two')['project'],root/'games/two')
                self.assertEqual(c.resolve(project=root/'games/two')['id'],'two')

    def test_reject_absolute_and_escaping_project(self):
        for value in ['C:/Games/Test','../escape','']:
            with self.assertRaises(ValueError): c.relative_path(value,True)

    def test_disabled(self):
        data={'default_game':'x','games':{'x':dict(project='games/x',installation='..',enabled=False)}}
        with patch.object(c,'read',return_value=data):
            with self.assertRaises(ValueError): c.resolve()

if __name__=='__main__': unittest.main()
