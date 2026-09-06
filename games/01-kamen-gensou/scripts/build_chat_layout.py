"""Identify structural chat headers from original name/color/prompt commands."""
import pipeline as p

def generate(commands):
    headers=[]; unmatched=[]
    for i,c in enumerate(commands):
        if c['opcode']!=72 or not c['strings'] or not (c['strings'][0] or '').startswith('＞'): continue
        if i>=3 and commands[i-1]['opcode']==81 and commands[i-2]['opcode']==72 and commands[i-3]['opcode']==80 and commands[i-2]['script']==c['script']:
            name=commands[i-2]
            headers.append(dict(script=c['script'],instruction=name['instruction'],name=name['strings'][0],prompt=c['instruction']))
        else:unmatched.append(dict(script=c['script'],instruction=c['instruction']))
    p.require(not unmatched,'Unrecognized chat message headers: '+str(unmatched))
    keys=[x['script']+':'+str(x['instruction']) for x in headers]
    code='using System.Collections.Generic;\nnamespace Kibu1ZhCN {\npublic static class ChatLayout {\n'
    code+='private static readonly HashSet<string> Headers = new HashSet<string> {\n'
    code+=',\n'.join('"'+k+'"' for k in keys)
    code+='\n};\npublic static bool IsHeader(string script,int instruction) { return Headers.Contains(script+":"+instruction); }\n}\n}\n'
    (p.WORK/'bepinex/src/ChatLayout.cs').write_text(code,encoding='utf-8')
    p.save(p.WORK/'reports/chat_layout.json',dict(headers=headers,count=len(headers),unmatched=unmatched))

if __name__=='__main__':generate(p.load(p.WORK/'bepinex/build/replay.json')['commands'])
