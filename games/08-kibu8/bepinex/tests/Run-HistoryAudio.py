"""Run the real history open/close bodies with independent audio-clock doubles."""
from pathlib import Path
import subprocess
root=Path(__file__).resolve().parents[4]
source=(root/'engine/adapters/gmode-20050817/src/HistoryRuntime.cs').read_text(encoding='utf-8-sig')
opening=source[source.index('        private void OpenHistory('):source.index('        private static bool BeforeCanvasInput')]
closing=source[source.index('        protected override void Close()'):source.index('        private static bool BeforeInput')].replace('protected override void','private void')
program=r'''using System;
using System.Reflection;
using UnityEngine;
using KibukawaHistory;
namespace UnityEngine {
 public class AudioSource { public bool mute,isPlaying=true; public bool Audible {get{return isPlaying&&!mute;}} }
 public static class Time {public static float timeScale=1;public static int frameCount=1;}
}
namespace KibukawaHistory { }
class EventSystem { public static EventSystem current=new EventSystem();public bool enabled=true; }
class Display {public object currentFrame;}
class Presenter {public AudioSource audioSource=new AudioSource();}
class Canvas {public static Presenter[] phraseTrack={new Presenter(),new Presenter()};}
class Test {
 object canvas=new Canvas(),display=new Display();
 FieldInfo currentFrame=typeof(Display).GetField("currentFrame");
 bool open,bottom,eventsEnabled;int openedFrame,closedInputFrame;float previousScale;EventSystem events;
 AUDIO_FIELD
 static FieldInfo Field(object value,string name) {return value.GetType().GetField(name,BindingFlags.Instance|BindingFlags.Static|BindingFlags.Public|BindingFlags.NonPublic);}
 bool RefreshSoftKeyHint(){return true;} void ClearKeys(){}
 OPEN
 CLOSE
 static void Check(bool ok,string message){if(!ok){Console.WriteLine(message);Environment.Exit(1);}}
 static void Main(){
  var t=new Test();((Display)t.display).currentFrame=t.canvas;
  t.OpenHistory();
  for(int frame=0;frame<120;frame++) Check(!Canvas.phraseTrack[1].audioSource.Audible,"FAIL: text sound remains audible while history is open");
  Check(Canvas.phraseTrack[0].audioSource.Audible,"BGM changed");t.Close();
  Check(Canvas.phraseTrack[1].audioSource.Audible,"Text sound not restored");
  Canvas.phraseTrack[1].audioSource.mute=true;t.OpenHistory();t.Close();
  Check(Canvas.phraseTrack[1].audioSource.mute,"Existing mute lost");
  Console.WriteLine("PASS: history suppresses text audio for 120 frames, preserves BGM and restores prior mute state");
 }
}'''.replace('OPEN',opening).replace('CLOSE',closing)
field='        private readonly HistoryAudioMute historyAudio = new HistoryAudioMute();'
program=program.replace('AUDIO_FIELD',field if field in source else '')
out=root/'games/08-kibu8/bepinex/build/history-audio';out.mkdir(parents=True,exist_ok=True)
cs=out/'Test.cs';cs.write_text(program,encoding='utf-8-sig');exe=out/'Test.exe'
extra=root/'engine/adapters/gmode-v2/src/HistoryAudioMute.cs'
files=[str(cs)]+([str(extra)] if extra.exists() else [])
subprocess.run(['C:/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe','/nologo','/out:'+str(exe),*files],check=True)
subprocess.run([str(exe)],check=True)
