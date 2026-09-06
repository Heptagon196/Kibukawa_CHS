"""Validate every original help sprite and compile its reviewed Chinese content."""
import hashlib
import json
from pathlib import Path
import UnityPy
import pipeline as p

ROOT = p.WORK / 'bepinex'

def build_help_pages():
    data = p.load(ROOT / 'help-pages.zh-CN.json')
    bundle = p.GAME / data['bundle']
    p.require(hashlib.sha256(bundle.read_bytes()).hexdigest() == data['bundle_sha256'], 'Help bundle source mismatch')
    env = UnityPy.load(str(bundle))
    objects = {obj.path_id: obj for obj in env.objects}
    model = objects[data['data_model_path_id']].read_typetree()
    refs = model['howToPlayImages']
    p.require(len(refs) == len(data['pages']) == 4, 'Untranslated help pages detected')
    entries = []
    def q(value): return json.dumps(value, ensure_ascii=False)
    for ref, page in zip(refs, data['pages']):
        obj = objects[ref['m_PathID']]
        tree = obj.read_typetree()
        p.require(obj.path_id == page['sprite_path_id'] and tree['m_Name'] == page['sprite_name'], 'Help sprite order/name mismatch')
        tr = page['translation']
        p.require(tr['title'] and (tr.get('rows') or tr.get('paragraphs')), 'Empty help page')
        rows = tr.get('rows')
        if rows:
            p.require(len(rows) == 5 and all(r['key'] and r['action'] for r in rows), 'Incomplete control table')
            row_code = 'new string[][] { ' + ', '.join('new [] { '+q(r['key'])+', '+q(r['action'])+' }' for r in rows) + ' }'
        else:
            row_code = 'null'
        body = '\n\n'.join(([tr['heading']] if tr.get('heading') else []) + tr.get('paragraphs', []))
        entries.append('new HelpPage { Name='+q(page['sprite_name'])+', Title='+q(tr['title'])+', Subtitle='+q(tr.get('subtitle',''))+', Rows='+row_code+', Footer='+q(tr.get('footer',''))+', Body='+q(body)+' }')
    source = '''// Generated from help-pages.zh-CN.json by build_help_pages.py.
namespace Kibu1ZhCN {
    public sealed class HelpPage {
        public string Name, Title, Subtitle, Footer, Body;
        public string[][] Rows;
    }
    public static class HelpPages {
        public static readonly HelpPage[] All = new HelpPage[] {
            ''' + ',\n            '.join(entries) + '''
        };
        public static HelpPage Find(string name) {
            foreach (var page in All) if (page.Name == name) return page;
            return null;
        }
    }
}
'''
    p.inside(ROOT/'src/HelpPages.cs').write_text(source, encoding='utf-8-sig')
    report = dict(page_count=len(refs), translated_pages=len(entries), source_bundle_sha256=data['bundle_sha256'], sprite_names=[x['sprite_name'] for x in data['pages']], runtime_visual_tested=False)
    p.save(ROOT/'build/help-pages-report.json',report)
    return report

if __name__ == '__main__': print(json.dumps(build_help_pages(), ensure_ascii=False))
