"""Reject Japanese kana in shipped translated strings, including help overlays.

Source keys remain Japanese for runtime matching. Kanji shared with Chinese cannot
be classified by Unicode alone; this guard complements contextual language review.
"""
import re
import pipeline as p

JAPANESE = re.compile(r'[\u3040-\u30ff\uff66-\uff9f\u3005\u303b]')

def validate(cache, help_pages):
    failures=[]; checked=0; help_count=0
    def check(text, location):
        if JAPANESE.search(text):
            failures.append(dict(location=location,text=text,characters=sorted(set(JAPANESE.findall(text)))))
    for item in p.items(cache):
        if item['translation_status'] not in (1,2): continue
        checked+=1
        check(item['translated_text'],f'cache:{item["text_index"]}')
    def walk(value, location):
        nonlocal help_count
        if isinstance(value,str):
            help_count+=1;check(value,location)
        elif isinstance(value,dict):
            for k,v in value.items(): walk(v,location+'.'+k)
        elif isinstance(value,list):
            for i,v in enumerate(value): walk(v,location+f'[{i}]')
    for page in help_pages['pages']:
        walk(page['translation'],f'help:{page["page"]}')
    return dict(checked_translations=checked,checked_help_strings=help_count,
                failure_count=len(failures),failures=failures,
                scope='Translated cache values and help overlay text; excludes source matching keys and original image lettering. Shared Han characters require contextual review.')

def audit():
    report=validate(p.load(p.WORK/'work/cache.json'),p.load(p.WORK/'bepinex/help-pages.zh-CN.json'))
    p.save(p.WORK/'reports/japanese_residue.json',report)
    p.require(not report['failures'],'Japanese residue in translations; see reports/japanese_residue.json')
    return report

if __name__=='__main__':
    result=audit()
    print(f'PASS: {result["checked_translations"]} translations and {result["checked_help_strings"]} help strings contain no kana.')
