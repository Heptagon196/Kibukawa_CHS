"""Regression for the original eight-row opening email card."""
import unittest
import pipeline as p
ROWS=['【发件人】','amiami','【主题】','给床子亲','【正文】','我在桥町的这里，','快来哦(⌒▽⌒','「９８７８」']
class EmailLayout(unittest.TestCase):
    def test_email_rows(self):
        report=p.load(p.WORK/'bepinex/build/dialogue-reflow-report.json')
        pages=[r for r in report['pages'] if r['script']=='scn10' and r['instruction']==4589]
        self.assertEqual(len(pages),1)
        self.assertEqual(pages[0]['rows'],ROWS)
if __name__=='__main__':unittest.main()
