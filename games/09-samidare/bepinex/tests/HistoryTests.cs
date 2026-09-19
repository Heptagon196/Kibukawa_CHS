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
        public static string[] command = { "", "", "返回" };
        public static FakeAudio[] phraseTrack = { new FakeAudio(), new FakeAudio() };

        public void ClearBunBuffer()
        {
            for (int i = 0; i < Bun_moji.Length; i++) Bun_moji[i] = String.Empty;
        }

        public void KeyFlush() { }
        public void ProcessEvent(int type, int param) { }

        public FakeHistoryCanvas()
        {
            for (int i = 0; i < Lines; i++) Bun_iro[i] = new int[32];
            ColorTable[7] = 0x00ff0000;
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
        public static void BufferCleared(object canvas) { AfterBufferCleared(canvas); }
        public static void Load(object canvas) { AfterLoad(canvas); }
        public static void Drawn(object canvas, int keta, int dan) { AfterDrawnCharacter(canvas, keta, dan); }
        public static bool Game(object canvas, ref bool result) { return BeforeGame(canvas, ref result); }
        public static bool CanvasInput(object canvas, int type, int param) { return BeforeCanvasInput(canvas, type, param); }

        public HistoryBuffer Buffer { get { return history; } }
        public void SetOpen(bool value) { open = value; }
        public bool IsOpen { get { return open; } }
        public void BindNative(FakeHistoryCanvas canvas, Socotra.UI.StDisplay display)
        {
            Type runtime = typeof(Gmode20050117HistoryRuntime);
            runtime.GetField("canvasType", BindingFlags.NonPublic | BindingFlags.Instance).SetValue(this, typeof(FakeHistoryCanvas));
            runtime.GetField("displayType", BindingFlags.NonPublic | BindingFlags.Instance).SetValue(this, typeof(Socotra.UI.StDisplay));
            runtime.GetField("canvas", BindingFlags.NonPublic | BindingFlags.Instance).SetValue(this, canvas);
            runtime.GetField("display", BindingFlags.NonPublic | BindingFlags.Instance).SetValue(this, display);
            runtime.GetField("currentFrame", BindingFlags.NonPublic | BindingFlags.Instance).SetValue(this, typeof(Socotra.UI.StDisplay).GetField("currentFrame"));
            runtime.GetField("leftLabel", BindingFlags.NonPublic | BindingFlags.Instance).SetValue(this, typeof(Socotra.UI.StDisplay).GetField("softKey1Label"));
            runtime.GetField("keypadState", BindingFlags.NonPublic | BindingFlags.Instance).SetValue(this, typeof(Socotra.UI.StDisplay).GetField("keypadState"));
            UnityEngine.Object.found = display;
        }
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
            for (int i = 0; i < text.Length; i++) canvas.Bun_iro[dan][i] = 0x00ff0000;
            HistoryHarness.Text(canvas);          // BUNSYOU postfix runs before the draws
            for (int keta = 0; keta < text.Length; keta++) HistoryHarness.Drawn(canvas, keta, dan);
        }

        /// <summary>The one-shot ClearBunBuffer call ended an utterance.</summary>
        private static void Utterance(HistoryHarness harness, FakeHistoryCanvas canvas)
        {
            canvas.ClearBunBuffer();
            HistoryHarness.BufferCleared(canvas);
        }

        /// <summary>Stock a line and reveal it without running the utterance terminator.</summary>
        private static void Stock(HistoryHarness harness, FakeHistoryCanvas canvas, int dan, string text)
        {
            canvas.Bun_moji[dan] = text;
            canvas.Bun_nagasa[dan] = text.Length;
            for (int i = 0; i < text.Length; i++) canvas.Bun_iro[dan][i] = 0x00ff0000;
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

            // 2. PERIOD/ASTERISK are called once per frame while the last line is
            //    still revealing. Those waiting calls do not clear the buffer, so
            //    every redraw must remain in one entry and emit the speaker once.
            canvas.NowNamae = 0;
            Stock(harness, canvas, 0, "个，你是…？");
            for (int reveal = 0; reveal < 6; reveal++)
                for (int keta = 0; keta <= reveal; keta++) HistoryHarness.Drawn(canvas, keta, 0);
            Equal(2, harness.Buffer.Entries.Count, "multi-frame terminator wait stays in one entry");
            Equal("(晓)\n个，你是…？", harness.Buffer.Entries[1], "waiting terminator never splits characters or repeats the speaker");
            Utterance(harness, canvas);

            // 3. The next utterance emits the speaker again (or none when unset) and
            //    starts its own entry.
            canvas.NowNamae = -1;
            Line(harness, canvas, 2, "据新闻报道，");
            Utterance(harness, canvas);
            Equal(3, harness.Buffer.Entries.Count, "next utterance is its own entry");
            Equal("据新闻报道，", harness.Buffer.Entries[2], "no speaker prefix when no nameplate is set");

            // 4. ClearBunBuffer resets the coordinate dedupe. A new utterance may
            //    reuse the same (row, character) cells and must still be captured.
            Line(harness, canvas, 0, "坐标复用");
            Equal(4, harness.Buffer.Entries.Count, "cleared buffer permits coordinate reuse");
            Equal("坐标复用", harness.Buffer.Entries[3], "reused cells retain the new text");
            Utterance(harness, canvas);

            // 5. Only revealed characters are recorded: capture happens at the draw
            //    call, so unread text can never leak into the history.
            Stock(harness, canvas, 3, "这是大约八年来");
            HistoryHarness.Drawn(canvas, 0, 3);
            HistoryHarness.Drawn(canvas, 1, 3);
            Equal(5, harness.Buffer.Entries.Count, "undrawn remainder starts an entry with only what was revealed");
            Equal("这是", harness.Buffer.Entries[4], "only the two revealed characters were recorded");
            Utterance(harness, canvas);

            // 6. The opening title block is not drawn in reading order. The VM can
            //    visit the first and last cells of the three-fragment place line,
            //    redraw earlier rows, then fill the middle cells. History must sort
            //    the cells by (row, keta), while still excluding unseen cells.
            Stock(harness, canvas, 0, "２００４年６月某日");
            Stock(harness, canvas, 1, "天气：雨");
            Stock(harness, canvas, 2, "　");
            Stock(harness, canvas, 3, "鞠滨市鞠滨台");
            HistoryHarness.Drawn(canvas, 0, 3);
            HistoryHarness.Drawn(canvas, 5, 3);
            for (int keta = 0; keta < 9; keta++) HistoryHarness.Drawn(canvas, keta, 0);
            for (int keta = 0; keta < 4; keta++) HistoryHarness.Drawn(canvas, keta, 1);
            HistoryHarness.Drawn(canvas, 0, 2);
            for (int keta = 0; keta < 6; keta++) HistoryHarness.Drawn(canvas, keta, 3);
            Equal(6, harness.Buffer.Entries.Count, "out-of-order title redraw remains one entry");
            Equal("2004年6月某日\n天气：雨\n \n鞠滨市鞠滨台", harness.Buffer.Entries[5],
                "title rows and three-fragment place are rebuilt in native coordinate order");
            Utterance(harness, canvas);

            // 7. Bun_iro contains final 24-bit RGB values, while Namae_color is
            //    still a ColorTable index. Preserve both sides of an emphasis run.
            canvas.Namae_nafuda[0] = "(生王)";
            canvas.Namae_color[0] = 3;
            canvas.NowNamae = 0;
            Stock(harness, canvas, 0, "大哥哥叫生王正生");
            for (int keta = 0; keta < 4; keta++) canvas.Bun_iro[0][keta] = 0xffffff;
            for (int keta = 4; keta < 8; keta++) canvas.Bun_iro[0][keta] = 0xffff00;
            for (int keta = 0; keta < 8; keta++) HistoryHarness.Drawn(canvas, keta, 0);
            Equal(7, harness.Buffer.Entries.Count, "emphasised line creates one history entry");
            Equal("(生王)\n大哥哥叫生王正生", harness.Buffer.Entries[6], "real release line keeps its speaker and translated text");
            Equal(0x00ff00, harness.Buffer.Colors[6][0], "speaker colour still comes from Namae_color through the palette");
            Equal(0xffffff, harness.Buffer.Colors[6][5], "base body RGB is read directly from Bun_iro");
            Equal(0xffffff, harness.Buffer.Colors[6][8], "base colour survives the whole first run");
            Equal(0xffff00, harness.Buffer.Colors[6][9], "yellow emphasis begins at the translated split");
            Equal(0xffff00, harness.Buffer.Colors[6][12], "yellow emphasis survives the whole second run");
            Utterance(harness, canvas);

            // 8. The pause skips Game() but keeps the coroutine alive.
            harness.SetOpen(false);
            bool result = false;
            Check(HistoryHarness.Game(canvas, ref result), "Game runs normally while history is closed");
            harness.SetOpen(true);
            result = false;
            Check(!HistoryHarness.Game(canvas, ref result), "Game is skipped while history is open");
            Check(result, "Run() keeps looping because the skipped frame reports true");
            harness.SetOpen(false);

            // 9. The native SOFT1 route owns controller L shoulder plus keyboard
            //    Q/L. It opens on an inactive label, debounces holds, and closes on
            //    the next press without leaking that event to the game.
            HistoryHarness inputHarness = HistoryHarness.Create();
            FakeHistoryCanvas inputCanvas = new FakeHistoryCanvas();
            Socotra.UI.StDisplay display = new Socotra.UI.StDisplay();
            display.currentFrame = inputCanvas;
            display.softKey1Label.text = String.Empty;
            inputHarness.BindNative(inputCanvas, display);
            UnityEngine.EventSystems.EventSystem.current = new UnityEngine.EventSystems.EventSystem();
            display.keypadState = 1 << 21;
            UnityEngine.Time.frameCount = 10;
            UnityEngine.Time.timeScale = 1f;
            Check(!HistoryHarness.CanvasInput(inputCanvas, 1, 21), "native left softkey opening event is consumed");
            Check(inputHarness.IsOpen, "native left softkey opens history");
            Check(!UnityEngine.EventSystems.EventSystem.current.enabled, "history disables the underlying Unity UI input");
            Equal("历史记录", display.softKey1Label.text, "inactive left softkey displays history hint");
            Check(!HistoryHarness.CanvasInput(inputCanvas, 1, 21), "held softkey stays consumed without retoggling");
            Check(inputHarness.IsOpen, "held softkey does not close history");
            HistoryHarness.CanvasInput(inputCanvas, 2, 21);
            UnityEngine.Time.frameCount = 11;
            Check(!HistoryHarness.CanvasInput(inputCanvas, 1, 21), "second softkey press is consumed");
            Check(!inputHarness.IsOpen, "second softkey press closes history");
            Check(UnityEngine.EventSystems.EventSystem.current.enabled, "closing restores the underlying Unity UI input");
            result = false;
            Check(!HistoryHarness.Game(inputCanvas, ref result), "closing softkey frame is withheld from the VM");
            UnityEngine.Time.frameCount = 12;
            result = false;
            Check(!HistoryHarness.Game(inputCanvas, ref result), "held closing softkey remains withheld from the VM");
            display.keypadState = 0;
            HistoryHarness.CanvasInput(inputCanvas, 2, 21);
            UnityEngine.Time.frameCount = 13;
            result = false;
            Check(HistoryHarness.Game(inputCanvas, ref result), "VM resumes after the closing softkey is released");

            // Native Back and unrelated keys keep their original behaviour.
            HistoryHarness busyHarness = HistoryHarness.Create();
            display.softKey1Label.text = "返回";
            display.currentFrame = inputCanvas;
            busyHarness.BindNative(inputCanvas, display);
            UnityEngine.Time.frameCount = 20;
            Check(HistoryHarness.CanvasInput(inputCanvas, 1, 21), "busy native left softkey is not hijacked");
            Check(!busyHarness.IsOpen, "busy native label does not open history");
            HistoryHarness.CanvasInput(inputCanvas, 2, 21);
            UnityEngine.Time.frameCount = 21;
            Check(HistoryHarness.CanvasInput(inputCanvas, 1, 20), "unrelated native key is passed through");

            // 10. Out-of-range indices are ignored rather than throwing.
            HistoryHarness.Drawn(canvas, 99, 0);
            HistoryHarness.Drawn(canvas, 0, 99);
            HistoryHarness.Drawn(canvas, -1, 0);
            Check(true, "out-of-range draws did not throw");

            if (failures == 0) Console.WriteLine("PASS: ninth-game history capture, block grouping and pause verified offline.");
            else throw new InvalidOperationException(failures + " history regression check(s) failed");
        }
    }
}
