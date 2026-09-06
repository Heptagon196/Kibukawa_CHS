"""Replay proposed text edits independently of the installed/live translation."""
import pipeline as p
import subprocess

root=p.WORK/'work/ten_char_wait_review'
root.mkdir(exist_ok=True)
updates={x['text_index']:x['translated_text'] for x in p.load(p.WORK/'work/ten_char_wait_fixes.json')}
manifest=p.load(p.WORK/'work/manifest.json')
addresses={}
for e in manifest['entries']:
    if e['text_index'] not in updates: continue
    loc=e['location'];defs=manifest['definitions'][str(loc['opcode'])]
    addresses[(loc['member'],loc['instruction'],defs[:loc['argument']].count(3))]=updates[e['text_index']]
replay=p.load(p.WORK/'bepinex/build/replay.json')
for c in replay['commands']:
    for i in range(len(c['expected'])):
        key=(c['script'],c['instruction'],i)
        if key in addresses:c['expected'][i]=addresses[key]
p.save(root/'candidate-replay.json',replay)
subprocess.run([str(p.WORK/'bepinex/build/DialogueReflowTests.exe'),str(root/'candidate-replay.json'),str(root/'candidate-report.json')],check=True)
report=p.load(root/'candidate-report.json')
print('Additional waits:',[(x['script'],x['instruction']) for x in report['additionalWaitLocations']])
