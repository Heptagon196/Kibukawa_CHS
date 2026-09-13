"""Exercise common algorithms with independent page graphs and font metrics."""
from pathlib import Path
import subprocess
import unittest

class RuntimeCoreTests(unittest.TestCase):
    def test_common_policies(self):
        src=Path(__file__).parent/'src'
        program=r'''using System;
using Kibukawa.Engine.GmodeV2;
class Test {
 static void Check(bool value) { if(!value) throw new Exception("Common policy regression"); }
 static void Main() {
  var memory=new PageMemory(); int cursor,back;
  memory.SelectScript("a",new[]{new[]{99,10,20}});
  Check(memory.Begin(10)==10);
  Check(memory.Record(2,false,20,out back)); Check(memory.Begin(20)==20);
  Check(memory.Record(1,true,null,out back) && back==99);
  Check(memory.Begin(10)==20 && memory.Restore(5,out cursor) && cursor==1);
  // Explicit Previous must override remembered page; cursor count may shrink.
  memory.Record(4,false,10,out back); Check(memory.Begin(10)==10);
  memory.Record(3,true,null,out back);
  memory.SelectScript("b",new[]{new[]{7,100,200,300}});
  Check(memory.Begin(100)==100); memory.Record(0,false,300,out back);
  Check(memory.Begin(300)==300); memory.Record(2,true,null,out back);
  memory.SelectScript("a",null); Check(memory.Begin(10)==10);
  Check(memory.Restore(2,out cursor) && cursor==1);
  Check(memory.Begin(999)==999 && !memory.Restore(2,out cursor));
  Check(TextBreaks.Next("甲乙丙丁",0,24,c=>12,c=>false)==2);
  Check(TextBreaks.Next("甲乙丙丁",0,24,c=>8,c=>false)==3);
  Check(TextBreaks.Next("甲乙，丙",0,24,c=>12,c=>false)==1);
  Check(TextBreaks.Next("甲AB乙",0,24,c=>c<128?6:12,c=>c>='A'&&c<='Z')==3);
 }
}'''
        directory=Path(__file__).resolve().parents[3]/'games/08-kibu8/bepinex/build/common-tests'
        directory.mkdir(parents=True,exist_ok=True)
        cs=Path(directory)/'Test.cs';cs.write_text(program,encoding='utf-8')
        exe=Path(directory)/'Test.exe'
        subprocess.run(['C:/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe','/nologo','/out:'+str(exe),str(cs),str(src/'PageMemory.cs'),str(src/'TextBreaks.cs')],check=True)
        subprocess.run([str(exe)],check=True)
