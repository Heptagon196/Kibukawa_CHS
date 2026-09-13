// Offline regression for the ninth-game history capture: drives the production
// hooks in the order the shipped VM does, on a canvas that mirrors CanvasEx's
// fields, and inspects the resulting HistoryBuffer. No game assembly, no Unity.
using System;
using System.Collections.Generic;
using System.Reflection;
using KibukawaHistory;

namespace Kibu9ZenTests
{
    /// <summary>Mirrors the CanvasEx members the history glue reads.</summary>
    public sealed class FakeHistoryCanvas
    {
        public const int Lines = 4;
        public string[] Bun_moji = new string[Lines];
        public int[][] Bun_iro = new int[Lines][];
        public int[] Bun_nagasa = new int[Lines];
        public int NowNamae = -1;
        public string[] Namae_nafuda = new string[4];
        public int[] Namae_color = new int[4];
        public int[] ColorTable = new int[8];
        public int MainTask;
        public static FakeAudio[] phraseTrack = { new FakeAudio(), new FakeAudio() };

        public FakeHistoryCanvas()
        {
            for (int i = 0; i < Lines; i++) Bun_iro[i] = new int[32];
            ColorTable[7] = 0x00ff0000;     // body colour used by the tests
            ColorTable[3] = 0x0000ff00;     // speaker colour
        }
    }

    public sealed class FakeAudio { public UnityEngine.AudioSource audioSource = new UnityEngine.AudioSource(); }

    /// <summary>Exposes the protected hooks without changing production visibility.</summary>
    public sealed class HistoryHarness : Gmode20050117HistoryRuntime
    {
        public static HistoryHarness Create()
        {
            HistoryHarness harness = new HistoryHarness();
            typeof(Gmode20050117HistoryRuntime)
                .GetField("self", BindingFlags.NonPublic | BindingFlags.Static)
                .SetValue(null, harness);
            return harness;
        }

        public static void Text(object canvas) { AfterText(canvas); }
        public static void Line(object canvas) { AfterLine(canvas); }
        public static void Load(object canvas) { AfterLoad(canvas); }
        public static void Drawn(object canvas, int keta, int dan) { AfterDrawnCharacter(canvas, keta, dan); }
        public static bool Game(ref bool result) { return BeforeGame(null, ref result); }

        public HistoryBuffer Buffer { get { return history; } }
        public void SetOpen(bool value) { open = value; }
    }

    public static class HistoryTests
    {
        private static int failures;

        private static void Check(bool condition, string message)
        {
            if (condition) return;
            failures++;
            Console.WriteLine("FAIL: " + message);
        }

        private static void Equal(object expected, object actual, string message)
        {
            Check(Equals(expected, actual), message + " (expected " + Show(expected) + ", got " + Show(actual) + ")");
        }

        private static string Show(object value) { return value == null ? "<null>" : "'" + value + "'"; }

        /// <summary>Stock one display line and reveal every character, as the VM does.</summary>
        private static void Line(HistoryHarness harness, FakeHistoryCanvas canvas, int dan, string text)
        {
            canvas.Bun_moji[dan] = text;
            canvas.Bun_nagasa[dan] = text.Length;
            for (int i = 0; i < text.Length; i++) canvas.Bun_iro[dan][i] = 7;
            HistoryHarness.Text(canvas);          // BUNSYOU postfix runs before the draws
            for (int keta = 0; keta < text.Length; keta++) HistoryHarness.Drawn(canvas, keta, dan);
        }

        /// <summary>An utterance ended: BUNSYOU_PERIOD / BUNSYOU_ASTARISK cleared the buffer.</summary>
        private static void Utterance(HistoryHarness harness, FakeHistoryCanvas canvas) { HistoryHarness.Line(canvas); }

        /// <summary>Stock a line and reveal it without running the utterance terminator.</summary>
        private static void Stock(HistoryHarness harness, FakeHistoryCanvas canvas, int dan, string text)
        {
            canvas.Bun_moji[dan] = text;
            canvas.Bun_nagasa[dan] = text.Length;
            for (int i = 0; i < text.Length; i++) canvas.Bun_iro[dan][i] = 7;
            HistoryHarness.Text(canvas);
        }

        public static void Run(string gamePath)
        {
            HistoryHarness harness = HistoryHarness.Create();
            FakeHistoryCanvas canvas = new FakeHistoryCanvas();
            HistoryHarness.Load(canvas);
            canvas.Namae_nafuda[0] = "(晓)";
            canvas.Namae_color[0] = 3;
            canvas.NowNamae = 0;

            // 1. One utterance of two lines: the speaker is emitted once, the lines are
            //    separated, and colours come from the palette and Bun_iro.
            Stock(harness, canvas, 0, "天气：雨");
            for (int keta = 0; keta < 4; keta++) HistoryHarness.Drawn(canvas, keta, 0);
            // The renderer redraws visible characters every frame; a repeat must not duplicate.
            for (int keta = 0; keta < 4; keta++) HistoryHarness.Drawn(canvas, keta, 0);
            Line(harness, canvas, 1, "鞠滨市鞠滨台");
            Utterance(harness, canvas);
            Equal(1, harness.Buffer.Entries.Count, "one history entry per utterance");
            Equal("(晓)\n天气：雨\n鞠滨市鞠滨台", harness.Buffer.Entries[0], "speaker once, lines separated, no redraw duplication");
            Equal(0x0000ff00, harness.Buffer.Colors[0][0], "speaker colour comes from the palette");
            Equal(0x00ff0000, harness.Buffer.Colors[0][4], "body colour comes from Bun_iro");

            // 2. The next utterance emits the speaker again (or none when unset) and
            //    starts its own entry.
            canvas.NowNamae = -1;
            Line(harness, canvas, 2, "据新闻报道，");
            Utterance(harness, canvas);
            Equal(2, harness.Buffer.Entries.Count, "second utterance is its own entry");
            Equal("据新闻报道，", harness.Buffer.Entries[1], "no speaker prefix when no nameplate is set");

            // 3. Only revealed characters are recorded: capture happens at the draw
            //    call, so unread text can never leak into the history.
            Stock(harness, canvas, 3, "这是大约八年来");
            HistoryHarness.Text(canvas);
            HistoryHarness.Drawn(canvas, 0, 3);
            HistoryHarness.Drawn(canvas, 1, 3);
            Equal(3, harness.Buffer.Entries.Count, "undrawn remainder starts an entry with only what was revealed");
            Equal("这是", harness.Buffer.Entries[2], "only the two revealed characters were recorded");

            // 5. The pause skips Game() but keeps the coroutine alive.
            harness.SetOpen(false);
            bool result = false;
            Check(HistoryHarness.Game(ref result), "Game runs normally while history is closed");
            harness.SetOpen(true);
            result = false;
            Check(!HistoryHarness.Game(ref result), "Game is skipped while history is open");
            Check(result, "Run() keeps looping because the skipped frame reports true");
            harness.SetOpen(false);

            // 6. Out-of-range indices are ignored rather than throwing.
            HistoryHarness.Drawn(canvas, 99, 0);
            HistoryHarness.Drawn(canvas, 0, 99);
            HistoryHarness.Drawn(canvas, -1, 0);
            Check(true, "out-of-range draws did not throw");

            if (failures == 0) Console.WriteLine("PASS: ninth-game history capture, block grouping and pause verified offline.");
            else throw new InvalidOperationException(failures + " history regression check(s) failed");
        }
    }
}
