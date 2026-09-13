using System;
using System.Reflection;
using Kibu8ZhCN;
using Kibukawa.Engine.UnityUI;
namespace HarmonyLib {
 public class Harmony { public Harmony(string id){} public void UnpatchSelf(){} public void Patch(MethodBase m,HarmonyMethod a,HarmonyMethod b){} }
 public class HarmonyMethod {public int priority; public HarmonyMethod(Type t,string n){} }
 public static class Priority {public const int First=0;}
 public static class AccessTools {
  public static Type TypeByName(string n){return null;}
  public static MethodInfo PropertySetter(Type t,string n){return t.GetProperty(n).GetSetMethod();}
  public static MethodInfo Method(Type t,string n){return t.GetMethod(n,BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Static|BindingFlags.Instance);}
  public static MethodInfo Method(Type t,string n,Type[] args){return t.GetMethod(n,args);}
 }
}
namespace UnityEngine {
 public class Object {public static void Destroy(Object o){} public static void DontDestroyOnLoad(Object o){} }
 public enum FontStyle {Normal}
 public class Font:Object {public static Font CreateDynamicFontFromOSFont(string[] names,int size){return new Font();}}
 public static class Time {public static float realtimeSinceStartup;}
 public static class Resources {public static T[] FindObjectsOfTypeAll<T>(){return new T[0];}}
 public static class Mathf {
  public static int Min(int a,int b){return Math.Min(a,b);}public static int Max(int a,int b){return Math.Max(a,b);}
  public static float Max(float a,float b){return Math.Max(a,b);}
 }
}
namespace UnityEngine.UI {
 public class InputField {public Text textComponent;}
 public class Text:UnityEngine.Object {
  public string text {get;set;} public UnityEngine.Font font; public int fontSize,resizeTextMinSize,resizeTextMaxSize;
  public float lineSpacing;public bool resizeTextForBestFit;public UnityEngine.FontStyle fontStyle;public InputField input;
  public T GetComponentInParent<T>() where T:class {return input as T;}
  public void OnEnable(){}
 }
}
class UiRuntimeTests {
 static void Check(bool value,string message){if(!value)throw new Exception(message);}
 static object Invoke(string method,params object[] args){return typeof(UiLocalizationRuntime).GetMethod(method,BindingFlags.NonPublic|BindingFlags.Static).Invoke(null,args);}
 static void Run(){
  UiLocalizationData.Exact.Clear();UiLocalizationData.Keys.Clear();
  UiLocalizationData.Exact.Add("原文","译文");UiLocalizationData.Exact.Add("「{0}」で宜しいですか？","确定使用“{0}”吗？");
  UiLocalization.Initialize();
  Check(UiLocalization.TranslateDisplay("原文")=="译文","exact translation");
  Check(UiLocalization.TranslateDisplay("前原文后")=="前原文后","no substring replacement");
  Check(UiLocalization.TranslateDisplay("「原文」で宜しいですか？")=="确定使用“原文”吗？","preserve entered name");
  Check(UiLocalization.TranslateDisplay("停止")=="停止","sentinel protection");
  bool conflict=false;try{UiLocalization.RegisterDisplayTranslation("原文","别的");}catch(InvalidOperationException){conflict=true;}
  Check(conflict,"conflict rejected");
  UiLocalization.RegisterDisplayTranslation("姓名","译名");Check(UiLocalization.TranslateDisplay("姓名")=="译名","registered name");
  var text=new UnityEngine.UI.Text{font=new UnityEngine.Font(),fontSize=18,lineSpacing=1,text="原文"};var original=text.font;
  object[] args={text,"原文"};Invoke("BeforeTextSet",args);text.text=(string)args[1];Invoke("AfterTextSet",text);
  Check(text.text=="译文" && text.font!=original,"label translated and font applied");
  var input=new UnityEngine.UI.Text();input.input=new UnityEngine.UI.InputField{textComponent=input};
  object[] entered={input,"原文"};Invoke("BeforeTextSet",entered);Check((string)entered[1]=="原文","input value preserved");
  char[] chars="x原文y".ToCharArray();object[] sliced={chars,1,2};Invoke("BeforeDrawChars",sliced);
  Check(new string((char[])sliced[0])=="译文" && new string(chars)=="x原文y","slice translation keeps source buffer");
  UiLocalization.Dispose();Check(text.text=="原文" && text.font==original && text.fontSize==18 && text.lineSpacing==1,"dispose restores UI");
  Check(UiLocalization.TranslateDisplay("姓名")=="姓名","dispose clears registration");
  Console.WriteLine("PASS: production UI runtime and game policy: exact text, name confirmation, input protection, source buffer, conflict and restoration");
 }
 public static int Main(){try{Run();return 0;}catch(Exception e){Console.WriteLine(e.ToString());return 1;}}
}
