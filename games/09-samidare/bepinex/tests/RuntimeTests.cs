// Offline regression for the ninth-game runtime: drives the production hooks in the
// exact order the shipped VM does, using the real translation pack and the real
// BunsyouStock semantics. No game assembly, no Unity, no window.
using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using Kibukawa.Engine.Gmode20050117;

namespace Kibu9ZenTests
{
    /// <summary>Exposes the protected hooks without changing production visibility.</summary>
    public sealed class Harness : CanvasRuntime
    {
        public static void Setup(string packPath, Type canvas)
        {
            canvasType = canvas;
            pack = RuntimePack.Load(packPath);
            ready = true;
        }

        public static void Load(object canvas, string scriptName) { BeforeLoad(canvas, scriptName); }
        public static void Name(object canvas) { BeforeName(canvas); }
        public static void Choice(object canvas) { BeforeChoice(canvas); }
        public static string Read(object canvas, string returned) { AfterStringRead(canvas, ref returned); return returned; }
        public static string Get(string key, string returned) { AfterGet(key, ref returned); return returned; }
        public static void NativeLiterals() { ApplyNativeLiterals(); }
        public static int Literals { get { return literals.Count; } }
        public static int PackLines { get { return pack == null ? -1 : pack.LineCount; } }
        public static string Script { get { return currentScript; } }
        public static int Offset { get { return lineOffset; } }
        public static bool Probe(string script, int offset, out string target, out int fragments)
        { return pack.TryLine(script, offset, out target, out fragments); }
        public static bool Rubi(object canvas, ref int result) { return BeforeCreateRubi(canvas, ref result); }
        public static void Bunsyou(object canvas) { BeforeBunsyou(canvas); }
        public static void Colour(object canvas) { BeforeColour(canvas); }
        public static string Stock(object canvas, string text) { BeforeStock(canvas, ref text); return text; }
        public static void EndLine(object canvas) { AfterLine(canvas); }
    }

    public static class RuntimeTests
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

        private static string Show(object value)
        {
            return value == null ? "<null>" : "'" + value + "'";
        }

        /// <summary>Drive one display line exactly as the VM does: BUNSYOU, fragments, terminator.</summary>
        private static string PlayLine(FakeCanvas canvas, int offset, int budget, int declared, string[] fragments)
        {
            canvas.Pos = offset + 1;                       // the dispatcher already consumed the opcode
            canvas.BunsyouNagasaMax = budget;
            canvas.Bun_nagasa[canvas.NowStockMojiDan] = declared;
            Harness.Bunsyou(canvas);
            var stocked = new StringBuilder();
            foreach (string fragment in fragments)
            {
                // The hook rewrites the argument, so the substituted value is what the
                // native stocking call receives.
                string text = Harness.Stock(canvas, fragment);
                canvas.BunsyouStock(text);
                stocked.Append(text);
            }
            Harness.EndLine(canvas);
            canvas.EndLine();
            return stocked.ToString();
        }

        /// <summary>Drive a recoloured line: the VM runs BUNSYOU_IRO between fragments.
        ///
        /// ``colourBefore[i]`` is the colour operand of the BUNSYOU_IRO that precedes
        /// fragment i, or 0 for none — exactly the shape the shipped scripts have.
        /// </summary>
        private static string PlayColourLine(FakeCanvas canvas, int offset, int budget, int declared,
                                             string[] fragments, int[] colourBefore)
        {
            canvas.Pos = offset + 1;
            canvas.BunsyouNagasaMax = budget;
            canvas.Bun_nagasa[canvas.NowStockMojiDan] = declared;
            Harness.Bunsyou(canvas);
            var stocked = new StringBuilder();
            for (int i = 0; i < fragments.Length; i++)
            {
                if (colourBefore[i] != 0)
                {
                    canvas.NextColour = colourBefore[i];
                    Harness.Colour(canvas);        // the prefix on BUNSYOU_IRO
                    canvas.BUNSYOU_IRO();          // the native handler it wraps
                }
                string text = Harness.Stock(canvas, fragments[i]);
                canvas.BunsyouStock(text);
                stocked.Append(text);
            }
            Harness.EndLine(canvas);
            canvas.EndLine();
            return stocked.ToString();
        }

        public static void Run(string packPath)
        {
            if (!File.Exists(packPath)) throw new FileNotFoundException("Build the smoke pack first", packPath);
            Harness.Setup(packPath, typeof(FakeCanvas));
            var canvas = new FakeCanvas();
            Harness.Load(canvas, "c0_00");

            // 1. A translated single-fragment line.
            canvas = new FakeCanvas();
            string text = PlayLine(canvas, 24, 9, 9, new[] { "２００４年６月某日" });
            Equal("２００４年６月某日", text, "date line translation");
            Equal(9, canvas.Bun_nagasa[0], "date line nagasa");

            // 2. A translated line whose budget shrinks the text.
            canvas = new FakeCanvas();
            text = PlayLine(canvas, 48, 9, 4, new[] { "天気、雨" });
            Equal("天气、雨", text, "weather line translation");
            Equal(4, canvas.Bun_nagasa[0], "weather line nagasa");

            // 3. A multi-fragment line: the whole translation lands on the first
            //    fragment, the continuations are blanked, and nothing is duplicated.
            canvas = new FakeCanvas();
            text = PlayLine(canvas, 81, 9, 6, new[] { "鞠浜", "市", "鞠浜台" });
            Equal("鞠滨市鞠滨台", text, "three-fragment place line");
            Equal(6, canvas.Bun_nagasa[0], "place line nagasa");
            Equal(6, canvas.SyoriMojiCount, "place line character count");
            for (int slot = 0; slot < 6; slot++)
                Check(canvas.Bun_iro[0][slot] == 1 && canvas.Bun_alpha[0][slot] == 1024,
                      "parallel plane filled at slot " + slot);

            // 4. An untranslated line passes through byte-for-byte, and its nagasa
            //    stays the native declared length.
            canvas = new FakeCanvas();
            const string japanese = "それは、ある年の梅雨のこと。";
            text = PlayLine(canvas, 0x7fff, 9, 14, new[] { japanese });
            Equal(japanese, text, "untranslated line untouched");
            Equal(14, canvas.Bun_nagasa[0], "untranslated nagasa equals the line length");

            // 5. A translated multi-fragment line followed by an untranslated one: the
            //    continuation counter must not leak into the next line.
            canvas = new FakeCanvas();
            string place = PlayLine(canvas, 81, 9, 6, new[] { "鞠浜", "市", "鞠浜台" });
            const string afterPlace = "それは、ある年の梅雨のこと。";
            string following = PlayLine(canvas, 0x7ffe, 9, 14, new[] { afterPlace });
            Equal("鞠滨市鞠滨台", place, "translated line before an untranslated one");
            Equal(afterPlace, following, "continuation counter does not leak into the next line");
            Equal(6, canvas.Bun_nagasa[0], "first line nagasa is preserved");
            Equal(14, canvas.Bun_nagasa[1], "second line nagasa is its own length");

            // 6. Two consecutive translated lines keep independent nagasa and text.
            canvas = new FakeCanvas();
            string first = PlayLine(canvas, 214, 9, 9, new[] { "ニュースによれば、" });
            string second = PlayLine(canvas, 238, 9, 8, new[] { "およそ８年ぶりの" });
            Equal("据新闻说，", first, "first consecutive line");
            Equal("大约是８年来", second, "second consecutive line");
            Equal(5, canvas.Bun_nagasa[0], "first line nagasa");
            Equal(6, canvas.Bun_nagasa[1], "second line nagasa");

            // 7. Reloading a script resets the line state instead of leaking it.
            canvas = new FakeCanvas();
            PlayLine(canvas, 172, 9, 9, new[] { "…もう、何日も雨が", "続いていた。" });
            Harness.Load(canvas, "c0_00");
            text = PlayLine(canvas, 214, 9, 9, new[] { "ニュースによれば、" });
            Equal("据新闻说，", text, "line state after a reload");

            // 8. An unknown script leaves every line alone.
            Harness.Load(canvas, "c9_99");
            canvas = new FakeCanvas();
            text = PlayLine(canvas, 48, 9, 4, new[] { "天気、雨" });
            Equal("天気、雨", text, "unknown script untouched");
            Harness.Load(canvas, "c0_00");

            // 9. The loader argument is normalised to the canonical script name.
            Harness.Load(canvas, "c0_00.bin");
            canvas = new FakeCanvas();
            Equal("天气、雨", PlayLine(canvas, 48, 9, 4, new[] { "天気、雨" }), "canonical name with extension");
            Harness.Load(canvas, "c0_00");
            canvas = new FakeCanvas();
            Equal("天气、雨", PlayLine(canvas, 48, 9, 4, new[] { "天気、雨" }), "canonical name is case-insensitive");

            // 10. A menu label is replaced where SENTAKUSI reads it.
            Harness.Load(canvas, "c0_00");
            canvas = new FakeCanvas();
            canvas.Pos = 2156 + 1;
            Harness.Choice(canvas);
            Equal("交谈", Harness.Read(canvas, "話す"), "menu label translated");
            canvas.Pos = 2201 + 1;
            Harness.Choice(canvas);
            Equal("中断", Harness.Read(canvas, "中断する"), "second menu label translated in its own call");

            // 11. An untranslated menu label is untouched.
            canvas = new FakeCanvas();
            canvas.Pos = 2183 + 1;                       // 呼ぶ, absent from the smoke pack
            Harness.Choice(canvas);
            Equal("呼ぶ", Harness.Read(canvas, "呼ぶ"), "untranslated menu label untouched");

            // 12. A nameplate replaces only the first of NAMAE_SETTEI's three strings.
            Harness.Load(canvas, "c5_01");
            canvas = new FakeCanvas();
            canvas.Pos = 20 + 1;
            Harness.Name(canvas);
            Equal("(蝼川内)", Harness.Read(canvas, "(螻川内)"), "nameplate translated");
            Equal("se_mes00", Harness.Read(canvas, "se_mes00"), "sound name left alone");
            Equal("str", Harness.Read(canvas, "str"), "image name left alone");
            Equal("その後", Harness.Read(canvas, "その後"), "context cleared after three reads");

            // 13. A nameplate is not rewritten while another script is loaded.
            Harness.Load(canvas, "c0_00");
            canvas = new FakeCanvas();
            canvas.Pos = 20 + 1;
            Harness.Name(canvas);
            Equal("(螻川内)", Harness.Read(canvas, "(螻川内)"), "nameplate untouched in another script");

            // 14. Unity UI text is replaced through the game's own localization lookup.
            Equal("继续游戏", Harness.Get("pause_menu_label_close", "閉じる"), "localization key translated");
            Equal("是", Harness.Get("common_dialog_yes_label", "はい"), "second localization key translated");
            Equal("ランク外", Harness.Get("ranking_unranked_label", "ランク外"), "unknown key keeps the game text");

            // 15. The soft-key labels the game hard-codes are replaced in place, and the
            //     sound-test literals are left alone.
            Harness.NativeLiterals();
            Equal("返回", FakeCanvas.command[2], "native soft-key literal replaced");
            Equal("♪ 0", FakeCanvas.command[3], "sound-test literal untouched");
            Equal("", FakeCanvas.command[0], "empty literal untouched");
            Check(Harness.Literals == 1, "exactly one native literal replaced");

            // 16. Ruby: the ruby command precedes its base BUNSYOU, so Pos identifies the
            //     base line. A translated base suppresses the Japanese reading by leaving
            //     the cell counter unchanged (rubi_info_kazu becomes zero); an untranslated
            //     base keeps its ruby.
            Harness.Load(canvas, "c0_00");
            canvas = new FakeCanvas();
            canvas.Pos = 48;                       // the translated "天気、雨" line
            canvas.RubiCreateCounter = 7;
            int result = 7;
            Check(!Harness.Rubi(canvas, ref result), "translated base suppresses ruby creation");
            Equal(7, result, "suppressed ruby leaves the cell counter unchanged");
            canvas.Pos = 2183;                     // the untranslated "呼ぶ" line
            result = 7;
            Check(Harness.Rubi(canvas, ref result), "untranslated base keeps its ruby");
            Equal(7, result, "original ruby creation is left to the game");

            // 17. A line the script recolours part-way through is stocked one colour run per
            //     fragment, so the emphasis lands on the translated words it falls on. The
            //     whole line cannot go into the first fragment: BUNSYOU_IRO would then
            //     recolour empty fragments and the emphasis would disappear.
            Harness.Load(canvas, "c0_00");
            canvas = new FakeCanvas();
            text = PlayColourLine(canvas, 2293, 8, 8,
                                  new[] { "…", "おじさん", "、誰？" }, new[] { 0, 2, 0 });
            Equal("…大叔，你是谁？", text, "recoloured line translation");
            Equal(8, canvas.Bun_nagasa[0], "recoloured line nagasa");
            Equal(8, canvas.SyoriMojiCount, "recoloured line character count");
            Check(text.IndexOf('\u0001') < 0, "the run separator never reaches the screen");
            Equal(1, canvas.Bun_iro[0][0], "the opening run keeps the line colour");
            for (int slot = 1; slot < 8; slot++)
                Equal(2, canvas.Bun_iro[0][slot], "the emphasised run carries colour 2 at slot " + slot);

            // 18. Three colour runs, the shape of the save-failure notice: the run index has
            //     to advance with the script, not just toggle.
            canvas = new FakeCanvas();
            text = PlayColourLine(canvas, 21644, 11, 11,
                                  new[] { "セーブに", "失敗", "しました。" }, new[] { 0, 7, 3 });
            Equal("保存失败了。", text, "three-run line translation");
            Equal(6, canvas.Bun_nagasa[0], "three-run line nagasa");
            Equal(1, canvas.Bun_iro[0][0], "first run colour");
            Equal(1, canvas.Bun_iro[0][1], "first run colour, second character");
            Equal(7, canvas.Bun_iro[0][2], "failure run colour");
            Equal(7, canvas.Bun_iro[0][3], "failure run colour, second character");
            Equal(3, canvas.Bun_iro[0][4], "closing run colour");
            Equal(3, canvas.Bun_iro[0][5], "closing run colour, second character");

            // 19. The run counter belongs to the line: a recoloured line must not leave the
            //     next line thinking its own colour already changed. The script restores the
            //     normal colour between them, which is what the stub does here.
            canvas = new FakeCanvas();
            PlayColourLine(canvas, 21644, 11, 11,
                           new[] { "セーブに", "失敗", "しました。" }, new[] { 0, 7, 3 });
            canvas.CurrentColour = 1;
            text = PlayLine(canvas, 48, 9, 4, new[] { "天気、雨" });
            Equal("天气、雨", text, "plain line after a recoloured one");
            Equal(4, canvas.Bun_nagasa[1], "the next line keeps its own nagasa");
            for (int slot = 0; slot < 4; slot++)
                Equal(1, canvas.Bun_iro[1][slot], "the next line is one colour, not split by the last");

            if (failures == 0) Console.WriteLine("PASS: ninth-game runtime substitution, nagasa, line state and in-line colour runs verified offline.");
            else throw new InvalidOperationException(failures + " runtime regression check(s) failed");
        }
    }
}
