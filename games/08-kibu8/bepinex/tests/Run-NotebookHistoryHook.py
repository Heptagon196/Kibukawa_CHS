"""Exercise the production callback body, including work before tracker.Draw.

Unity rendering is outside this seam; speaker lookups are counted, not mocked
as free work. Notebook draws must perform none, whatever dialogue preceded them.
"""
from pathlib import Path
import subprocess

series = Path(__file__).resolve().parents[4]
source = (series / 'engine/adapters/gmode-20050817/src/HistoryRuntime.cs').read_text(encoding='utf-8')
start = source.index('private static void AfterDrawnCharacter(')
end = source.index('protected void DisposeHistory', start)
callback = source[start:end]
out = Path(__file__).resolve().parent.parent / 'build/history-tests'
out.mkdir(parents=True, exist_ok=True)
harness = r'''
using System;
using System.Reflection;
using KibukawaHistory;
class Probe {
 static Probe self;
 object drawnCanvas;
 DrawnHistoryTracker drawn=new DrawnHistoryTracker();
 HistoryBuffer history=new HistoryBuffer(2000);
 int lookups;
 static FieldInfo Field(object c,string n) {return c.GetType().GetField(n);}
 static int Number(object c,string n) {return (int)Field(c,n).GetValue(c);}
 string TranslateSpeaker(string s) {lookups++;return s;}
 CALLBACK
 class Canvas {
  public int MainTask=17,NowNamae=0;
  public string[] bg_itigyougun_mojiretu={new string('字',53)},Namae_nafuda={"speaker"};
  public sbyte[][] bg_itigyougun_color={new sbyte[53]},bg_itigyougun_control={new sbyte[53]};
  public int[] ColorTable={0xffffff},Namae_color={0};
 }
 static void Main() {
  foreach(int prior in new[]{0,20,53}) {
   self=new Probe();var c=new Canvas();self.drawnCanvas=c;self.drawn.Begin();
   for(int i=0;i<prior;i++)self.drawn.Draw(self.history,0,i,'前',0,null,0);
   for(int frame=0;frame<60;frame++)for(int i=0;i<53;i++)AfterDrawnCharacter(c,i,i,0);
   if(self.lookups!=0){Console.WriteLine("FAIL: Notebook performed "+self.lookups+" speaker resolutions; prior dialogue chars="+prior);Environment.Exit(1);}
   c.MainTask=0;self.drawn.Begin();AfterDrawnCharacter(c,0,0,0);
   if(self.lookups!=1)throw new Exception("Normal dialogue capture no longer resolves speaker");
  }
  Console.WriteLine("PASS: notebook hook performs zero speaker resolutions across prior dialogue states; dialogue resumes");
 }
}
'''.replace('CALLBACK', callback)
cs = out / 'NotebookHistoryHook.cs'
cs.write_text(harness, encoding='utf-8-sig')
exe = out / 'NotebookHistoryHook.exe'
subprocess.run(['C:/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe', '/nologo', '/out:'+str(exe), str(cs), str(series/'engine/adapters/gmode-20050817/src/HistoryCapture.cs'), str(series/'engine/adapters/gmode-v2/src/HistoryState.cs'), str(series/'engine/history/src/HistoryBuffer.cs'), str(series/'engine/history/src/RuntimePolicy.cs')], check=True)
subprocess.run([str(exe)], check=True)
