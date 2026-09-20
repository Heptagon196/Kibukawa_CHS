using System;
using System.Reflection;
using System.Runtime.CompilerServices;
using HarmonyLib;
using Kibukawa8.Runtime;
using Kibukawa.Engine.Gmode20050817;

namespace Kibukawa.Engine.Gmode20050817Direct
{
    // The row planes and renderer are the August engine's shared implementation.
    // Only installation and the direct (non-IEnumerator) INFO painter differ.
    public abstract class DirectCanvasRuntime : CanvasRuntime
    {
        [ThreadStatic] private static int bodyDrawDepth;
        [ThreadStatic] private static bool speakerDraw;
        [ThreadStatic] private static bool menuMeasure;
        protected struct DirectDrawState { internal float Scale; internal int BodyDepth; }
        sealed class Viewport { internal int Top; internal object Script; }
        static readonly ConditionalWeakTable<object,Viewport> viewports=new ConditionalWeakTable<object,Viewport>();
        protected void InstallDirectHooks(string owner)
        {
            harmony = new Harmony(owner);
            DirectChoiceMemory.Install(harmony, canvasType);
            // Retain native font sizes, spacing and alignment modes for choices.
            // Only their CP932-based width count needs a Unicode-safe equivalent.
            harmony.Patch(AccessTools.Method(canvasType,"PaintLongCommand"),prefix:new HarmonyMethod(typeof(DirectCanvasRuntime),"BeforeMenuMeasure"),finalizer:new HarmonyMethod(typeof(DirectCanvasRuntime),"RestoreMenuMeasure"));
            // PaintSentaku right-aligns the selected scenario subtitle with
            // Strlen(text)*6. CP932 cannot encode Chinese, so the native helper
            // counts each translated ideograph as a one-byte '?' and pushes most
            // of the label beyond the right edge. Use the same full/half-cell
            // measurement only while this page is being painted.
            harmony.Patch(AccessTools.Method(canvasType,"PaintSentaku"),prefix:new HarmonyMethod(typeof(DirectCanvasRuntime),"BeforeMenuMeasure"),finalizer:new HarmonyMethod(typeof(DirectCanvasRuntime),"RestoreMenuMeasure"));
            harmony.Patch(AccessTools.Method(canvasType,"Strlen",new[]{typeof(string)}),prefix:new HarmonyMethod(typeof(DirectCanvasRuntime),"BeforeMenuLength"));
            Patch(AccessTools.Method(canvasType,"Ds_sub"),"BeforeShadowString",null);
            Patch(AccessTools.Method(canvasType,"Ds_sub2"),"BeforeShadowString",null);
            // PaintMenu sends full labels through DocomoString, which then draws
            // one character at a time. Translate before that split so exact UI
            // entries such as volume and return actions can match.
            Patch(AccessTools.Method(canvasType,"DocomoString"),"BeforeShadowString",null);
            Patch(AccessTools.Method(canvasType,"LoadScenario"),null,"AfterLoad");
            Patch(AccessTools.Method(canvasType,"LoadResScenario"),null,"AfterLoad");
            harmony.Patch(AccessTools.Method(canvasType,"StringRead"),
                prefix:new HarmonyMethod(typeof(DirectCanvasRuntime),"BeforeDirectString"),
                postfix:new HarmonyMethod(typeof(DirectCanvasRuntime),"AfterDirectString"));
            harmony.Patch(AccessTools.Method(canvasType,"BUNSYOU"),prefix:new HarmonyMethod(typeof(CanvasRuntime),"BeforeDialogue"),postfix:new HarmonyMethod(typeof(DirectCanvasRuntime),"AfterDirectDialogue"));
            Patch(AccessTools.Method(canvasType,"BUNSYOU_ROLL"),"BeforeRoll","AfterRoll");
            harmony.Patch(AccessTools.Method(canvasType,"DrawAdvString"),prefix:new HarmonyMethod(typeof(DirectCanvasRuntime),"BeforeDirectDraw"),finalizer:new HarmonyMethod(typeof(DirectCanvasRuntime),"RestoreDirectScale"));
            harmony.Patch(AccessTools.Method(canvasType,"PaintADV"),prefix:new HarmonyMethod(typeof(DirectCanvasRuntime),"BeforeDirectViewport"));
            harmony.Patch(AccessTools.Method(canvasType,"PaintADV_text"),prefix:new HarmonyMethod(typeof(DirectCanvasRuntime),"BeforeDirectPaintText"));
            harmony.Patch(AccessTools.Method(canvasType,"DrawAdvNafuda"),prefix:new HarmonyMethod(typeof(DirectCanvasRuntime),"BeforeDirectSpeaker"),finalizer:new HarmonyMethod(typeof(DirectCanvasRuntime),"RestoreDirectSpeaker"));
            harmony.Patch(AccessTools.Method(canvasType,"DrawAdvStringRoll"),prefix:new HarmonyMethod(typeof(DirectCanvasRuntime),"BeforeDirectRollDraw"),finalizer:new HarmonyMethod(typeof(DirectCanvasRuntime),"RestoreDirectScale"));
            Type graphics=AccessTools.TypeByName("Socotra.UI.StGraphics");
            drawOrigin=AccessTools.Field(graphics,"drawOrigin");
            if(drawOrigin==null) throw new MissingFieldException("StGraphics.drawOrigin");
            harmony.Patch(AccessTools.Method(graphics,"DrawCharImpl",new[]{typeof(char[]),typeof(int),typeof(int)}),prefix:new HarmonyMethod(typeof(DirectCanvasRuntime),"BeforeDraw"));
            foreach(string method in layout.SmallFontMethods)
                Patch(AccessTools.Method(canvasType,method),"BeforeSmallFontPage",null,"RestoreSmallFontPage");
            harmony.Patch(AccessTools.Method(canvasType,"PaintMain_info"),prefix:new HarmonyMethod(typeof(DirectCanvasRuntime),"DrawDirectInfo"));
        }
        protected static void AfterDirectDialogue(object __instance,ReadState __state)
        {
            var state=State(__instance);state.Dialogue=false;
            if(__state==null)__state=RecoverDirectDialogue(__instance,state);
            if(__state==null)return;
            var original=__state.Display.Rows;
            int capacity=layout.DialogueRows-(Number(__instance,"NowNamae")==-1?0:1);
            int width=Number(__instance,"MojiHani_yoko")==0?204:220;
            // Full-screen/vertical pages also carry handset-width soft rows.
            // Reflow them with their original row count as the ceiling: this
            // merges obsolete breaks without applying the ordinary dialogue
            // page budget or adding rows. DirectTextLayout itself preserves
            // semantic punctuation, controls, indentation and spaced cards.
            if(Number(__instance,"MojiHani_tate")!=0)capacity=original.Length;
            var rows=DirectTextLayout.Wrap(original,width,capacity);
            int maximum=0;
            for(int i=0;i<rows.Length;i++){ApplyRow(__instance,rows[i],i,false,false);maximum=Math.Max(maximum,rows[i].Text.Length);}
            int end=Math.Max(rows.Length+1,((string[])F("bg_itigyougun_mojiretu").GetValue(__instance)).Length);
            var empty=new RuntimeRow{Text="",SourceText="",Colors=new byte[0],Controls=new byte[0],RubyJson="{}"};
            for(int i=rows.Length;i<end;i++)ApplyRow(__instance,empty,i,false,false);
            F("BunsyouGun_gyousuu").SetValue(__instance,checked((sbyte)rows.Length));
            F("BunsyouGun_max_mojisuu").SetValue(__instance,checked((sbyte)maximum));
            state.Dialogue=true;state.Reflowed=rows.Length!=original.Length;
        }
        static ReadState RecoverDirectDialogue(object canvas,CanvasState state)
        {
            // If a non-story page reaches BUNSYOU with a command position that
            // does not identify the display, the native parser still supplies
            // the exact source rows at postfix time. Bind those rows back to one
            // unique display without touching Script or Pos; ambiguity retains
            // the original text.
            if(state.Translation==null)return null;
            int count=Number(canvas,"BunsyouGun_gyousuu");
            var source=(string[])F("bg_itigyougun_mojiretu").GetValue(canvas);
            if(source==null || count<1 || count>source.Length)return null;
            DisplayTranslation match=null;
            foreach(var display in state.Translation.Displays.Values)
            {
                if(display.Opcode!=255 || display.Rows.Length!=count)continue;
                bool equal=true;
                for(int i=0;i<count;i++)
                    if(!String.Equals(source[i],display.Rows[i].SourceText,StringComparison.Ordinal)){equal=false;break;}
                if(!equal)continue;
                if(match!=null)return null;
                match=display;
            }
            return match==null?null:new ReadState{Display=match,Row=0};
        }
        protected static void BeforeDirectViewport(object __instance)
        {
            if(!ready || !State(__instance).Dialogue || Number(__instance,"MojiHani_tate")!=0)return;
            var view=viewports.GetOrCreateValue(__instance);
            var script=F("Script").GetValue(__instance);
            int current=Math.Min(Number(__instance,"PrintDanYoyaku"),Number(__instance,"BunsyouGun_gyousuu")-1);
            int visible=layout.DialogueRows-(Number(__instance,"NowNamae")==-1?0:1);
            int top=Math.Max(0,current-visible+1);
            if(view.Top!=top || !Object.ReferenceEquals(view.Script,script)) F("Resumed").SetValue(__instance,true);
            view.Script=script;view.Top=top;
        }
        protected static void BeforeDirectPaintText(object __instance)
        {
            if(!ready || !State(__instance).Dialogue)return;
            int row=Number(__instance,"PrintDanYoyaku");
            int count=Number(__instance,"BunsyouGun_gyousuu");
            if(row<0 || row>=count)return;
            // This direct engine can leave the completed-row cursor on the
            // preceding row after a translated buffer changes row lengths.
            // PaintADV_text then returns before drawing, while Game_adv keeps
            // advancing the character cursor until its swallowed bounds error
            // repeats every frame. Synchronize only at a pristine row start;
            // active text, waits and click controls remain native-driven.
            if(Number(__instance,"PrintDanKanryo")!=row && Number(__instance,"PrintMojiKetaKanryo")<0)
                F("PrintDanKanryo").SetValue(__instance,row);
        }
        protected static bool BeforeDirectDraw(object __instance,int __2,int __3,ref int __4,ref int __5,out DirectDrawState __state)
        {
            __state=new DirectDrawState { Scale=drawScale, BodyDepth=bodyDrawDepth };
            if(!ready || !State(__instance).Dialogue || smallFontScope)return true;
            bodyDrawDepth++;
            if(Number(__instance,"MojiHani_tate")==0)
            {
                int top=viewports.GetOrCreateValue(__instance).Top;
                if(__3<top)return false;
                __5=134+(Number(__instance,"NowNamae")==-1?0:layout.RowAdvance)+(__3-top)*layout.RowAdvance;
            }
            if(Number(__instance,"MojiHani_tate")==0)FitDirectText(__instance,__2,__3,false,ref __4);
            return true;
        }
        protected static void FitDirectText(object canvas,int slot,int row,bool roll,ref int x)
        {
            var state=State(canvas);
            if(roll?!state.RollRows.Contains(row):!state.Dialogue)return;
            var lines=(string[])F(roll?"rollitigyougun_mojiretu":"bg_itigyougun_mojiretu").GetValue(canvas);
            string text=lines[row];int align=roll?1:Number(canvas,"MojiHani_yoko");
            int width=DirectTextLayout.Measure(text,0,text.Length),maximum=width;
            if(!roll && align==0)
                for(int i=0;i<Number(canvas,"BunsyouGun_gyousuu");i++)
                    if(lines[i]!=null)maximum=Math.Max(maximum,DirectTextLayout.Measure(lines[i],0,lines[i].Length));
            double start=align==0?10+(204-maximum)/2.0:align==3?10:align==2?230-width:(240-width)/2.0;
            x=(int)Math.Round(start+DirectTextLayout.Position(text,slot),MidpointRounding.AwayFromZero);
            drawScale=1f;
        }
        protected static void RestoreDirectScale(DirectDrawState __state)
        { RestoreScale(__state.Scale); bodyDrawDepth=__state.BodyDepth; }
        protected static void BeforeDirectRollDraw(object __instance,int __2,int __3,ref int __4,out DirectDrawState __state)
        {
            __state=new DirectDrawState { Scale=drawScale, BodyDepth=bodyDrawDepth };
            if(!ready)return;
            if(State(__instance).RollRows.Contains(__3))bodyDrawDepth++;
            if(Number(__instance,"MojiHani_tate")==0)FitDirectText(__instance,__2,__3,true,ref __4);
        }
        // Body and speaker use 16px. Everywhere else the shared renderer selects
        // the atlas from the native StFont size (12px or 16px).
        protected new static bool BeforeDraw(object __instance,char[] __0,int __1,int __2)
        {
            if(!ready)return true;
            bool body=bodyDrawDepth>0 && !smallFontScope;
            var origin=(UnityEngine.Vector2)drawOrigin.GetValue(__instance);
            return Kibu1ZhCN.LegacyFontRenderer.Draw(__instance,__0,__1+(int)origin.x,__2+(int)origin.y,
                null,font,body && !speakerDraw && drawScale>0?drawScale:1f,body || speakerDraw?null:smallFont);
        }
        protected static void BeforeDirectSpeaker(object __instance,int __1,ref int __2,out bool __state)
        {
            __state=speakerDraw;
            if(ready)speakerDraw=true;
            if(ready && State(__instance).Dialogue && Number(__instance,"MojiHani_tate")==0)__2=134;
        }
        protected static void RestoreDirectSpeaker(bool __state) { speakerDraw=__state; }
        protected static void BeforeMenuMeasure(out bool __state) { __state=menuMeasure;menuMeasure=true; }
        protected static void RestoreMenuMeasure(bool __state) { menuMeasure=__state; }
        protected static bool BeforeMenuLength(string __0,ref int __result)
        {
            if(!ready || !menuMeasure || __0==null)return true;
            int units=0;
            foreach(char c in __0)
            {
                if(c=='\0')break;
                units+=(c>=' ' && c<='~' || c>='\uff61' && c<='\uff9f')?1:2;
            }
            __result=units;
            return false;
        }
        protected static void BeforeDirectString(object __instance,out int __state) { __state=Number(__instance,"Pos"); }
        protected static void AfterDirectString(object __instance,int __state,ref string __result)
        {
            if(!ready) return;
            var script=State(__instance).Translation;
            StringTranslation text;
            if(script!=null && script.Strings.TryGetValue(__state,out text) &&
                (text.Opcode==5 || text.Opcode==8 || text.Opcode==73))
            {
                if(__result!=text.Source) throw new InvalidOperationException("Original string binding mismatch");
                __result=text.Target;
            }
        }
        protected static bool DrawDirectInfo(object __instance,object __0)
        {
            if(!ready) return true;
            RuntimeRow row;
            string source=(string)F("info_struct_moji").GetValue(__instance);
            if(source==null || !infoRows.TryGetValue(source,out row)) return true;
            if(Number(__instance,"FrameTask")!=2 || Number(__instance,"MainTask")==11 ||
                (bool)F("NowRoll").GetValue(__instance)) return false;
            int width=0;
            foreach(char c in row.Text) width+=LatinMetrics.NotebookWidth(c,layout.InfoAdvance);
            int x=238-width;
            int[] palette=(int[])F("ColorTable").GetValue(__instance);
            MethodInfo color=AccessTools.Method(canvasType,"SetColor");
            MethodInfo draw=AccessTools.Method(__0.GetType(),"DrawString",new[]{typeof(string),typeof(int),typeof(int)});
            bool previous=smallFontScope;
            smallFontScope=true;
            try
            {
                for(int i=0;i<row.Text.Length;i++)
                {
                    color.Invoke(__instance,new object[]{__0,palette[row.Colors[i]]});
                    draw.Invoke(__0,new object[]{row.Text[i].ToString(),x,layout.InfoBaseline});
                    x+=LatinMetrics.NotebookWidth(row.Text[i],layout.InfoAdvance);
                }
            }
            finally { smallFontScope=previous; }
            return false;
        }
    }
}
