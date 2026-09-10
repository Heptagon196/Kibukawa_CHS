using System;
using Kibu1ZhCN;
namespace UnityEngine {
 public class Font {}
 public enum FontStyle { Normal, Bold }
 public static class Mathf { public static int Min(int a,int b){return Math.Min(a,b);} public static int Max(int a,int b){return Math.Max(a,b);} public static float Max(float a,float b){return Math.Max(a,b);} }
}
namespace UnityEngine.UI {
 public class Text { public UnityEngine.Font font; public int fontSize=14,resizeTextMinSize=10,resizeTextMaxSize=40; public float lineSpacing=1; public bool resizeTextForBestFit; public UnityEngine.FontStyle fontStyle; public string name="Label",text=""; }
}
class FontLifecycleTest {
 static int Main(){try { Run();return 0; } catch(Exception e){Console.WriteLine("FAIL: "+e.Message);return 1;}}
 static void Run(){
  var text=new UnityEngine.UI.Text();
  UiFontPolicy.Capture(text); // OnEnable fires before runtime labels are initialized.
  var intended=new UnityEngine.Font();var fallback=new UnityEngine.Font();
  text.font=intended;text.fontSize=32;text.text="ABC";
  UiFontPolicy.Apply(text,fallback);
  if(text.font!=intended || text.fontSize!=32)throw new Exception("Runtime ASCII key lost its assigned font/size after early OnEnable");
  text.text="标题";UiFontPolicy.Apply(text,fallback);
  if(text.font!=fallback)throw new Exception("Chinese fallback lost");
  text.text="2";UiFontPolicy.Apply(text,fallback);
  if(text.font!=intended || text.fontSize!=32)throw new Exception("Numeric key font was not restored");
  var pending=new UnityEngine.UI.Text();UiFontPolicy.Apply(pending,fallback);
  UiFontPolicy.Reset();if(text.font!=intended)throw new Exception("Reset lost font");
  Console.WriteLine("PASS runtime label initialization: empty font, ASCII, Chinese fallback, numeric restore and reset");
 }
}
