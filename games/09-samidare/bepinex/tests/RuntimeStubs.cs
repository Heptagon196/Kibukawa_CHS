// Test-only dependencies for the ninth-game runtime regression.
// Never included in the plugin build and never loads a game assembly.
using System;
using System.Reflection;

namespace BepInEx
{
    public class BepInPlugin : Attribute { public BepInPlugin(string a, string b, string c) { } }
    public class BepInProcess : Attribute { public BepInProcess(string a) { } }
    public class BaseUnityPlugin { public ConfigStub Config = new ConfigStub(); public InfoStub Info = new InfoStub(); public LogStub Logger = new LogStub(); }
    public class ConfigStub { public ValueStub Bind(string a, string b, bool c, string d) { return new ValueStub { Value = c }; } }
    public class ValueStub { public bool Value; }
    public class InfoStub { public string Location; }
    public class LogStub { public void LogInfo(object v) { } public void LogWarning(object v) { } public void LogError(object v) { } }
    public static class Paths { public static string GameRootPath; }
}

namespace HarmonyLib
{
    public class Harmony
    {
        public Harmony(string s) { }
        public void UnpatchSelf() { }
        public void Patch(MethodBase original, HarmonyMethod prefix = null, HarmonyMethod postfix = null,
                          HarmonyMethod transpiler = null, HarmonyMethod finalizer = null, HarmonyMethod ilmanipulator = null) { }
    }
    public class HarmonyMethod : Attribute
    {
        public HarmonyMethod(Type t, string s) { }
        public HarmonyMethod(MethodInfo m) { }
    }
    /// <summary>Opcode/operand pair the choice-memory transpiler rewrites.</summary>
    public class CodeInstruction
    {
        public System.Reflection.Emit.OpCode opcode;
        public object operand;
        public CodeInstruction() { }
        public CodeInstruction(System.Reflection.Emit.OpCode code, object value = null) { opcode = code; operand = value; }
    }
    public static class AccessTools
    {
        public static FieldInfo Field(Type t, string s) { return t.GetField(s, BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.Static); }
        public static Type TypeByName(string s) { return Type.GetType(s); }
        public static MethodInfo Method(Type t, string s) { return t == null ? null : t.GetMethod(s); }
        public static MethodInfo Method(Type t, string s, Type[] p) { return t == null ? null : t.GetMethod(s, p); }
    }
}

namespace UnityEngine
{
    public struct Vector2 { public float x, y; public Vector2(float a, float b) { x = a; y = b; } }
}

namespace Kibu1ZhCN
{
    public sealed class BitmapFontAtlas
    {
        public BitmapFontAtlas(string p) { }
        public int GlyphCount { get { return 0; } }
        public void Dispose() { }
    }
    public static class LegacyFontRenderer
    {
        public static bool Draw(object graphics, char[] text, int x, int y, object fallback,
                                BitmapFontAtlas bitmap = null, float scale = 1f,
                                BitmapFontAtlas small = null, float? top = null) { return false; }
    }
}

namespace Kibukawa.Engine.Gmode20050117
{
    /// <summary>
    /// Stand-in for the shipped CanvasEx: only the members the runtime resolves and
    /// the native stocking behaviour it relies on, so the production hooks can run
    /// off-line without Unity or the game assembly.
    /// </summary>
    public sealed class FakeCanvas
    {
        public const int Lines = 8;
        public const int Columns = 32;
        public int Pos;
        public int BunsyouNagasaMax;
        public int DanNoKazu;
        public int NowStockMojiDan;
        public int NowStockMojiKeta;
        public int NowPrintingDan;
        public int NowPrintingKeta;
        public int SyoriMojiCount;
        public int RubiCreateCounter;
        public string[] Bun_moji = new string[Lines];
        public int[] Bun_nagasa = new int[Lines];
        public int[][] Bun_iro = NewPlanes();
        public int[][] Bun_speed = NewPlanes();
        public int[][] Bun_alpha = NewPlanes();
        public int[][] Bun_jikan = NewPlanes();
        public static int FWidth = 17;
        public static int FHeight = 16;
        public static int FAscent = 12;
        /// <summary>Colour the next stocked characters carry, as BUNSYOU_IRO sets it.</summary>
        public int CurrentColour = 1;
        /// <summary>The operand the next BUNSYOU_IRO reads from the script.</summary>
        public int NextColour = 1;
        /// <summary>Same literals CanvasEx::.cctor writes into its soft-key array.</summary>
        public static string[] command = { "", "", "戻る", "♪ 0", "♪ 1", "♪ 2", "♪ 3" };

        private static int[][] NewPlanes()
        {
            var planes = new int[Lines][];
            for (int i = 0; i < Lines; i++) planes[i] = new int[Columns];
            return planes;
        }

        /// <summary>Native CanvasEx::BunsyouStock: append and fill the parallel planes.</summary>
        public void BunsyouStock(string text)
        {
            int dan = NowStockMojiDan;
            int start = NowStockMojiKeta;
            Bun_moji[dan] = (Bun_moji[dan] ?? string.Empty) + text;
            for (int i = 0; i < text.Length; i++)
            {
                int slot = start + i;
                if (slot >= Columns) break;
                Bun_iro[dan][slot] = CurrentColour;
                Bun_speed[dan][slot] = 0;
                Bun_alpha[dan][slot] = 1024;
                Bun_jikan[dan][slot] = 0;
            }
            NowStockMojiKeta += text.Length;
            SyoriMojiCount += text.Length;
        }

        /// <summary>Native CanvasEx::BUNSYOU_IRO: recolour the characters stocked after it.</summary>
        public void BUNSYOU_IRO() { CurrentColour = NextColour; }

        /// <summary>The terminators that advance the dan index in the shipped game.</summary>
        public void EndLine() { NowStockMojiKeta = 0; NowStockMojiDan++; }
    }
}
