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
            graphicsType = typeof(FakeGraphics);
            drawOrigin = typeof(FakeGraphics).GetField("drawOrigin");
            pack = RuntimePack.Load(packPath);
            font = new Kibu1ZhCN.BitmapFontAtlas("dialogue-16");
            smallFont = new Kibu1ZhCN.BitmapFontAtlas("ui-12");
            ready = true;
        }

        public static void Load(object canvas, string scriptName) { BeforeLoad(canvas, scriptName); }
        public static void Name(object canvas) { BeforeName(canvas); }
        public static void Choice(object canvas) { BeforeChoice(canvas); }
        public static string Read(object canvas, string returned) { AfterStringRead(canvas, ref returned); return returned; }
        public static string Get(string key, string returned) { AfterGet(key, ref returned); return returned; }
        public static string CanvasUi(string text) { BeforeCanvasUi(ref text); return text; }
        public static void NativeLiterals() { ApplyNativeLiterals(); }
        public static int Literals { get { return literals.Count; } }
        public static int PackLines { get { return pack == null ? -1 : pack.LineCount; } }
        public static string Script { get { return currentScript; } }
        public static int Offset { get { return lineOffset; } }
        public static bool Probe(string script, int offset, out string target, out int fragments)
        { return pack.TryLine(script, offset, out target, out fragments); }
        public static string ExpectedLine(string script, int offset, string fallback)
        {
            string target;
            int fragments;
            return pack.TryLine(script, offset, out target, out fragments) ? target : fallback;
        }
        public static string ExpectedLocalization(string key, string fallback)
        {
            string target;
            return pack.TryLocalization(key, out target) ? target : fallback;
        }
        public static bool Rubi(object canvas, ref int result) { return BeforeCreateRubi(canvas, ref result); }
        public static void Bunsyou(object canvas) { BeforeBunsyou(canvas); }
        public static void Colour(object canvas) { BeforeColour(canvas); }
        public static void F7(object canvas) { BeforeF7(canvas); }
        public static bool Colon(object canvas) { return BeforeColon(canvas); }
        public static string Stock(object canvas, string text) { BeforeStock(canvas, ref text); return text; }
        public static void EndLine(object canvas) { AfterLine(canvas); }
        public static bool Place(object canvas, int keta, int dan, ref int x, ref int y)
        { bool state; BeforeAdvDraw(canvas, keta, dan, ref x, ref y, out state); return state; }
        public static void ClearText(object canvas) { AfterClearText(canvas); }
        public static bool PlaceName(object canvas, ref int x, ref int y)
        { bool state; BeforeNameplatePosition(canvas, ref x, ref y, out state); return state; }
        public static void RestorePlace(bool state) { RestoreAdvDraw(state); }
        public static bool EnterNameplate()
        { bool state; BeforeNameplateDraw(out state); return state; }
        public static void RestoreNameplate(bool state) { RestoreNameplateDraw(state); }
        public static void Glyph(object graphics, int x, int y)
        { BeforeDraw(graphics, new[] { '中' }, x, y); }
        public static bool ChoiceCenter(object canvas, object graphics, int index, int y, int colour)
        { return BeforeChoiceCenter(canvas, graphics, index, y, colour); }
        public static bool ChoiceLeft(object canvas, object graphics, int index, int x, int y, int colour)
        { return BeforeChoiceLeft(canvas, graphics, index, x, y, colour); }
        public static object BeforeNativeSave(object canvas)
        {
            NameSaveState state;
            BeforeSaveNames(canvas, out state);
            return state;
        }
        public static void AfterNativeSave(object canvas, object state)
        { AfterSaveNames(canvas, (NameSaveState)state); }
        public static Exception FailedNativeSave(object canvas, object state, Exception error)
        { return AfterSaveNamesError(canvas, (NameSaveState)state, error); }
        public static void AfterNativeLoad(object canvas) { AfterLoadNames(canvas); }
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
                // CanvasEx::BUNSYOU charges SyoriMojiCount for the source before its
                // call to BunsyouStock reaches our prefix.
                canvas.CountSource(fragment);
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
        /// ``colourBefore[i]`` is the colour operand of BUNSYOU_IRO before fragment i,
        /// 0 for no transition, -1 for an F7 base-colour restore, or -2 for the first
        /// F7 that closes ruby without changing colour.
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
                if (colourBefore[i] > 0)
                {
                    canvas.NextColour = colourBefore[i];
                    Harness.Colour(canvas);        // the prefix on BUNSYOU_IRO
                    canvas.BUNSYOU_IRO();          // the native handler it wraps
                }
                else if (colourBefore[i] < 0)
                {
                    if (colourBefore[i] == -2) canvas.NowRubiChu = true;
                    Harness.F7(canvas);
                    canvas.BUNSYOU_F7();
                }
                canvas.CountSource(fragments[i]);
                string text = Harness.Stock(canvas, fragments[i]);
                canvas.BunsyouStock(text);
                stocked.Append(text);
            }
            Harness.EndLine(canvas);
            canvas.EndLine();
            return stocked.ToString();
        }

        /// <summary>Drive a line where F7 restores the base colour between fragments.</summary>
        private static string PlayResetLine(FakeCanvas canvas, int offset, int budget, int declared,
                                            string[] fragments, int colour, int resetBefore)
        {
            canvas.Pos = offset + 1;
            canvas.BunsyouNagasaMax = budget;
            canvas.Bun_nagasa[canvas.NowStockMojiDan] = declared;
            Harness.Bunsyou(canvas);
            canvas.CurrentColour = colour;
            canvas.NowMojiColorChangeChu = true;
            var stocked = new StringBuilder();
            for (int i = 0; i < fragments.Length; i++)
            {
                if (i == resetBefore)
                {
                    Harness.F7(canvas);
                    canvas.BUNSYOU_F7();
                }
                canvas.CountSource(fragments[i]);
                string text = Harness.Stock(canvas, fragments[i]);
                canvas.BunsyouStock(text);
                stocked.Append(text);
            }
            Harness.EndLine(canvas);
            canvas.EndLine();
            return stocked.ToString();
        }

        public static void Reflow(string packPath)
        {
            failures = 0;
            Harness.Setup(packPath, typeof(FakeCanvas));
            var canvas = new FakeCanvas();
            Harness.Load(canvas, "c0_01");
            canvas.DanNoKazu = 2;
            PlayLine(canvas, 1306, 8, 9, new[] { "…なんかひとりで" });
            int firstX = 0, firstY = 198;
            bool state = Harness.Place(canvas, 0, 0, ref firstX, ref firstY);
            Harness.RestorePlace(state);
            int earlyX = firstX, earlyY = firstY;
            PlayLine(canvas, 1328, 8, 9, new[] { "楽しそうですね。" });
            int continuedX = 0, continuedY = 222;
            state = Harness.Place(canvas, 0, 1, ref continuedX, ref continuedY);
            Harness.RestorePlace(state);
            Equal(222, continuedY, "segmented phrase starts on the planned second row");
            Equal(52, continuedX, "new phrase respects the authored left margin");
            firstX = 0; firstY = 198;
            state = Harness.Place(canvas, 0, 0, ref firstX, ref firstY);
            Harness.RestorePlace(state);
            Equal(earlyX, firstX, "stocking later rows never moves earlier glyphs horizontally");
            Equal(earlyY, firstY, "stocking later rows never moves earlier glyphs vertically");
            Equal(198, firstY, "first row remains inside the authored text block");
            int nameX = 52, nameY = 174;
            state = Harness.PlaceName(canvas, ref nameX, ref nameY);
            Harness.RestoreNameplate(state);
            Equal(52, nameX, "speaker aligns with reflowed text");
            Equal(174, nameY, "speaker moves with compact utterance");
            canvas.MojiHani_yoko = 2;
            int specialX = 0, specialY = 198;
            state = Harness.Place(canvas, 0, 0, ref specialX, ref specialY);
            Harness.RestorePlace(state);
            Equal(198, specialY, "special alignment preserves authored layout");
            canvas.MojiHani_yoko = 0;
            Harness.ClearText(canvas);
            int clearedX = 0, clearedY = 198;
            state = Harness.Place(canvas, 0, 0, ref clearedX, ref clearedY);
            Harness.RestorePlace(state);
            Equal(198, clearedY, "clear removes old mapping even if a buffer is reused");
            Harness.Load(canvas, "c0_02");
            int loadedX = 0, loadedY = 198;
            state = Harness.Place(canvas, 0, 0, ref loadedX, ref loadedY);
            Harness.RestorePlace(state);
            Equal(198, loadedY, "script changes do not inherit previous layout");
            canvas = new FakeCanvas();
            Harness.Load(canvas, "c0_01");
            canvas.DanNoKazu = 3;
            PlayLine(canvas, 7176, 8, 8, new[] { "今回のゲストは、" });
            PlayLine(canvas, 7198, 8, 8, new[] { "探偵助手の白鷺洲" });
            PlayLine(canvas, 7237, 8, 7, new[] { "伊綱さんです！" });
            int surnameX = 0, surnameY = 198, givenX = 0, givenY = 222;
            state = Harness.Place(canvas, 4, 1, ref surnameX, ref surnameY);
            Harness.RestorePlace(state);
            state = Harness.Place(canvas, 0, 2, ref givenX, ref givenY);
            Harness.RestorePlace(state);
            Equal(222, surnameY, "surname moves out of its native row to stay with full name");
            Equal(surnameY, givenY, "full name joins across two native storage rows");
            Equal(surnameX + 51, givenX, "given name follows the three-character surname");

            // Full-screen narration uses the whole viewport and must not inherit the
            // ordinary dialogue pagination click.  The colon handler may finish the
            // progressive reveal, but once all glyphs are visible it must continue
            // without displaying a cursor or waiting for input.
            canvas = new FakeCanvas {
                MojiHani_tate = 1, SyoriMojiCount = -1, MainTask = 6, SubTask = 7,
                SysCursor_enable = true, OsippanasiKinsi = true
            };
            Check(!Harness.Colon(canvas), "full-screen colon bypasses the pagination wait");
            Equal(0, canvas.MainTask, "full-screen colon releases the main task");
            Equal(0, canvas.SubTask, "full-screen colon releases the input subtask");
            Check(!canvas.SysCursor_enable, "full-screen colon hides the click cursor");
            Check(!canvas.OsippanasiKinsi, "full-screen colon clears the held-key guard");

            canvas = new FakeCanvas { MojiHani_tate = 0, SyoriMojiCount = -1 };
            Check(Harness.Colon(canvas), "ordinary dialogue retains its authored colon wait");

            canvas = new FakeCanvas { MojiHani_tate = 2, SyoriMojiCount = 1 };
            Check(Harness.Colon(canvas), "full-screen colon still lets the native reveal finish");

            canvas = new FakeCanvas { MojiHani_tate = 1, SyoriMojiCount = -1, NowFadeChu = true };
            Check(Harness.Colon(canvas), "full-screen colon still lets the native fade finish");
            if (failures != 0) throw new InvalidOperationException(failures + " reflow regressions");
            Console.WriteLine("PASS: real release utterance reflow, progressive reveal, speaker, clear and special alignment.");
        }

        public static void Run(string packPath)
        {
            if (!File.Exists(packPath)) throw new FileNotFoundException("Build the smoke pack first", packPath);
            Harness.Setup(packPath, typeof(FakeCanvas));
            var canvas = new FakeCanvas();
            Harness.Load(canvas, "c0_00");
            string weatherTarget = Harness.ExpectedLine("c0_00", 48, "天気、雨");

            // 1. A translated single-fragment line.
            canvas = new FakeCanvas();
            string text = PlayLine(canvas, 24, 9, 9, new[] { "２００４年６月某日" });
            Equal("２００４年６月某日", text, "date line translation");
            Equal(9, canvas.Bun_nagasa[0], "date line nagasa");

            // 2. A translated line whose budget shrinks the text.
            canvas = new FakeCanvas();
            text = PlayLine(canvas, 48, 9, 4, new[] { "天気、雨" });
            Equal(weatherTarget, text, "weather line translation");
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
            string secondTarget = Harness.ExpectedLine("c0_00", 238, "およそ８年ぶりの");
            Equal("据新闻说，", first, "first consecutive line");
            Equal(secondTarget, second, "second consecutive line");
            Equal(5, canvas.Bun_nagasa[0], "first line nagasa");
            Equal(secondTarget.Length, canvas.Bun_nagasa[1], "second line nagasa");

            // 7. Reloading a script resets the line state instead of leaking it.
            canvas = new FakeCanvas();
            text = PlayLine(canvas, 172, 9, 9, new[] { "…もう、何日も雨が" });
            Equal("…这雨已经下了", text, "intro rain line translation");
            Equal(7, canvas.SyoriMojiCount, "intro rain line pending character count");
            canvas.RevealStockedLine(0);
            Check(canvas.SyoriMojiCount < 0, "intro rain line reveal reaches the terminator state");
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
            Equal(weatherTarget, PlayLine(canvas, 48, 9, 4, new[] { "天気、雨" }), "canonical name with extension");
            Harness.Load(canvas, "c0_00");
            canvas = new FakeCanvas();
            Equal(weatherTarget, PlayLine(canvas, 48, 9, 4, new[] { "天気、雨" }), "canonical name is case-insensitive");

            // 10. A menu label is replaced where SENTAKUSI reads it.
            Harness.Load(canvas, "c0_00");
            canvas = new FakeCanvas();
            canvas.Pos = 2156 + 1;
            Harness.Choice(canvas);
            Equal("交谈", Harness.Read(canvas, "話す"), "menu label translated");
            canvas.Pos = 2201 + 1;
            Harness.Choice(canvas);
            Equal("中断", Harness.Read(canvas, "中断する"), "second menu label translated in its own call");

            // 11. A menu operand absent from the pack is untouched.
            canvas = new FakeCanvas();
            canvas.Pos = 0x7fff + 1;
            Harness.Choice(canvas);
            Equal("未収録", Harness.Read(canvas, "未収録"), "untranslated menu label untouched");

            // 12. A nameplate replaces only the first of NAMAE_SETTEI's three strings.
            Harness.Load(canvas, "c5_01");
            canvas = new FakeCanvas();
            canvas.Pos = 20 + 1;
            Harness.Name(canvas);
            Equal(Harness.ExpectedLine("c5_01", 20, "(螻川内)"),
                  Harness.Read(canvas, "(螻川内)"), "nameplate translated");
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
            Equal(Harness.ExpectedLocalization("pause_menu_label_close", "閉じる"),
                  Harness.Get("pause_menu_label_close", "閉じる"), "localization key translated");
            Equal("是", Harness.Get("common_dialog_yes_label", "はい"), "second localization key translated");
            Equal(Harness.ExpectedLocalization("ranking_unranked_label", "ランク外"),
                  Harness.Get("ranking_unranked_label", "ランク外"), "ranking label follows the active pack");
            Equal("未収録", Harness.Get("missing_key", "未収録"), "unknown key keeps the game text");

            // 14b. Ds_sub and Ds_sub2 receive one complete status line before they
            //     measure its width and split it into single-character DrawString
            //     calls. Translate at that boundary so neither centering nor glyph
            //     splitting can hide the original Japanese from the lookup.
            Equal("正在解压数据", Harness.CanvasUi("データ展開中"),
                  "Ds_sub complete UI line translated before native measurement");
            Equal("■　正在检查数据……　■", Harness.CanvasUi("■　データ確認中…　■"),
                  "Ds_sub2 decorated UI line translated as one string");
            Equal("未収録", Harness.CanvasUi("未収録"), "unknown canvas UI is untouched");

            // 15. The soft-key labels the game hard-codes are replaced in place, and the
            //     sound-test literals are left alone.
            Harness.NativeLiterals();
            Equal("返回", FakeCanvas.command[2], "native soft-key literal replaced");
            Equal("♪ 0", FakeCanvas.command[3], "sound-test literal untouched");
            Equal("", FakeCanvas.command[0], "empty literal untouched");
            Check(Harness.Literals == 1, "exactly one native literal replaced");

            // 16. Ruby: the Chinese edition suppresses every Japanese reading by leaving
            //     the cell counter unchanged (rubi_info_kazu becomes zero). This remains
            //     true before a line, between colour fragments and at unknown offsets.
            Harness.Load(canvas, "c0_00");
            canvas = new FakeCanvas();
            canvas.Pos = 48;                       // the translated "天気、雨" line
            canvas.RubiCreateCounter = 7;
            int result = 7;
            Check(!Harness.Rubi(canvas, ref result), "translated base suppresses ruby creation");
            Equal(7, result, "suppressed ruby leaves the cell counter unchanged");
            canvas = new FakeCanvas();
            canvas.Pos = 3087 + 1;
            Harness.Bunsyou(canvas);
            canvas.CountSource("うわあ");
            Equal("哇啊", Harness.Stock(canvas, "うわあ"), "screenshot line first colour run translated");
            Harness.Colour(canvas);
            canvas.Pos = 3109;                    // ruby is between translated fragments
            canvas.RubiCreateCounter = 11;
            result = 99;
            Check(!Harness.Rubi(canvas, ref result),
                  "mid-line ruby over translated 伊纲 is suppressed from active line state");
            Equal(11, result, "mid-line ruby leaves the cell counter unchanged");
            Harness.Load(canvas, "c0_00");       // reset the active translated line
            canvas.Pos = 0x7fff;                   // an offset absent from the pack
            canvas.RubiCreateCounter = 13;
            result = 7;
            Check(!Harness.Rubi(canvas, ref result), "unknown offset still suppresses Japanese ruby");
            Equal(13, result, "global ruby suppression leaves the current cell counter unchanged");

            // 17. A line the script recolours part-way through is stocked one colour run per
            //     fragment, so the emphasis lands on the translated words it falls on. The
            //     whole line cannot go into the first fragment: BUNSYOU_IRO would then
            //     recolour empty fragments and the emphasis would disappear.
            Harness.Load(canvas, "c0_00");
            canvas = new FakeCanvas();
            text = PlayColourLine(canvas, 2293, 8, 8,
                                  new[] { "…", "おじさん", "、誰？" }, new[] { 0, 2, -1 });
            Equal("…大叔，你是谁？", text, "recoloured line translation");
            Equal(8, canvas.Bun_nagasa[0], "recoloured line nagasa");
            Equal(8, canvas.SyoriMojiCount, "recoloured line character count");
            Check(text.IndexOf('\u0001') < 0, "the run separator never reaches the screen");
            Equal(1, canvas.Bun_iro[0][0], "the opening run keeps the line colour");
            Equal(2, canvas.Bun_iro[0][1], "the first emphasized character carries colour 2");
            Equal(2, canvas.Bun_iro[0][2], "the second emphasized character carries colour 2");
            for (int slot = 3; slot < 8; slot++)
                Equal(1, canvas.Bun_iro[0][slot], "F7 restores base colour at slot " + slot);

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

            // 19. F7 first closes ruby without changing colour, then a later F7 restores
            //     BaseMojiColor. This is the exact shape of 螻川内忠雄|の名前も.
            Harness.Load(canvas, "c3_01");
            canvas = new FakeCanvas();
            text = PlayColourLine(canvas, 4243, 9, 9,
                                  new[] { "螻川内", "忠雄", "の名前も" }, new[] { 2, -2, -1 });
            Equal("蝼川内忠雄的名字", text, "ruby and colour F7 line translation");
            for (int slot = 0; slot < 5; slot++)
                Equal(2, canvas.Bun_iro[0][slot], "name remains emphasized at slot " + slot);
            for (int slot = 5; slot < 8; slot++)
                Equal(1, canvas.Bun_iro[0][slot], "name suffix returns to base at slot " + slot);

            // 20. The run counter belongs to the line: a recoloured line must not leave the
            //     next line thinking its own colour already changed. The script restores the
            //     normal colour between them, which is what the stub does here.
            Harness.Load(canvas, "c0_00");
            canvas = new FakeCanvas();
            PlayColourLine(canvas, 21644, 11, 11,
                           new[] { "セーブに", "失敗", "しました。" }, new[] { 0, 7, 3 });
            canvas.CurrentColour = 1;
            text = PlayLine(canvas, 48, 9, 4, new[] { "天気、雨" });
            Equal(weatherTarget, text, "plain line after a recoloured one");
            Equal(4, canvas.Bun_nagasa[1], "the next line keeps its own nagasa");
            for (int slot = 0; slot < 4; slot++)
                Equal(1, canvas.Bun_iro[1][slot], "the next line is one colour, not split by the last");

            // 20. Match the eighth game's mixed-width policy: fullwidth Latin maps to
            //     halfwidth display cells, Latin/digits use 9px advances, Han uses 17px,
            //     and only Han/Latin boundaries gain a 9px visual blank.  The final
            //     dialogue atlas is lifted three pixels so the lowest outline pass
            //     leaves exactly three physical rows below its ink.
            canvas = new FakeCanvas();
            canvas.MojiHani_yoko = 3;              // native left-aligned mode
            canvas.Bun_moji[0] = "第３章M2";
            canvas.Bun_nagasa[0] = canvas.Bun_moji[0].Length;
            int[] expectedX = { 0, 26, 44, 70, 79 };
            for (int slot = 0; slot < expectedX.Length; slot++)
            {
                int x = 999, y = 222;
                bool drawState = Harness.Place(canvas, slot, 0, ref x, ref y);
                Equal(expectedX[slot], x, "eighth-game Latin placement at slot " + slot);
                Equal(222, y, "Latin placement keeps the native row origin at slot " + slot);
                Harness.Glyph(new FakeGraphics(), 0, 236);
                Equal(233, Kibu1ZhCN.LegacyFontRenderer.Y,
                      "dialogue glyph leaves three pixels below its lowest outline pass");
                Check(Kibu1ZhCN.LegacyFontRenderer.Small == null,
                      "dialogue keeps the 16px atlas");
                Harness.RestorePlace(drawState);
            }
            Harness.Glyph(new FakeGraphics(), 0, 236);
            Equal(236, Kibu1ZhCN.LegacyFontRenderer.Y, "non-dialogue UI glyph baseline is unchanged");
            Check(Kibu1ZhCN.LegacyFontRenderer.Small != null,
                  "non-dialogue UI receives the 12px atlas");
            bool nameState = Harness.EnterNameplate();
            Harness.Glyph(new FakeGraphics(), 0, 236);
            Check(Kibu1ZhCN.LegacyFontRenderer.Small == null,
                  "nameplate keeps the 16px atlas");
            Equal(236, Kibu1ZhCN.LegacyFontRenderer.Y,
                  "nameplate does not inherit the dialogue bottom lift");
            Harness.RestoreNameplate(nameState);
            Equal('3', LatinMetrics.Display('３'), "fullwidth digit display mapping");
            Equal(9, LatinMetrics.Width('３'), "fullwidth digit narrow advance");
            Equal(9, LatinMetrics.Width('M'), "ASCII letter narrow advance");
            Equal(17, LatinMetrics.Width('章'), "Han full advance");

            // 21. DanNoKazu is a count, not a last-row index. A stale wider string in
            //     Bun_moji[count] must not move an active centered block. Right-aligned
            //     mixed text still lands exactly on the 240px edge.
            canvas = new FakeCanvas();
            canvas.MojiHani_yoko = 0;
            canvas.DanNoKazu = 1;
            canvas.BunsyouNagasaMax = 1;
            canvas.Bun_moji[0] = "Ａ";
            canvas.Bun_moji[1] = "这是一条不属于当前对话的残留长行";
            int centeredX = 999, centeredY = 222;
            bool centeredState = Harness.Place(canvas, 0, 0, ref centeredX, ref centeredY);
            Equal(111, centeredX, "centered block uses the stable authored width");
            Harness.RestorePlace(centeredState);
            canvas.Bun_moji[1] = "后来才出现的较长一行";
            centeredX = 999;
            centeredState = Harness.Place(canvas, 0, 0, ref centeredX, ref centeredY);
            Equal(111, centeredX, "later stocked row does not move earlier centered text");
            Harness.RestorePlace(centeredState);
            canvas.MojiHani_yoko = 2;
            canvas.Bun_moji[0] = "第３";
            int rightX = 999, rightY = 222;
            bool rightState = Harness.Place(canvas, 0, 0, ref rightX, ref rightY);
            Equal(205, rightX, "right-aligned mixed row starts from its visual width");
            rightX = 999;
            Harness.RestorePlace(rightState);
            rightState = Harness.Place(canvas, 1, 0, ref rightX, ref rightY);
            Equal(231, rightX, "right-aligned final digit starts nine pixels before the edge");
            Harness.RestorePlace(rightState);

            // 22. Choices follow the eighth game's 12px-font 13/7px metrics, with its
            //     6px boundary blank. The ninth game's original outline and colour
            //     passes remain in place.
            canvas = new FakeCanvas();
            canvas.Sentaku_nafuda[0] = "伊纲妹妹ＬＯＶＥ！";
            var choiceGraphics = new FakeGraphics();
            Check(!Harness.ChoiceCenter(canvas, choiceGraphics, 0, 40, 0xabcdef),
                  "mixed-script centered choice uses the custom draw path");
            int[] choiceX = { 70, 83, 96, 109, 128, 135, 142, 149, 156 };
            int finalStart = choiceGraphics.X.Count - choiceX.Length;
            Equal(16 * choiceX.Length, choiceGraphics.X.Count, "choice keeps all native outline and colour passes");
            for (int i = 0; i < choiceX.Length; i++)
                Equal(choiceX[i], choiceGraphics.X[finalStart + i], "choice final-pass x at glyph " + i);
            Equal("L", choiceGraphics.Text[finalStart + 4], "fullwidth choice Latin maps to ASCII glyph");
            canvas.Sentaku_nafuda[1] = "继续调查";
            choiceGraphics = new FakeGraphics();
            Check(!Harness.ChoiceLeft(canvas, choiceGraphics, 1, 10, 40, 0xffffff),
                  "pure CJK choice avoids the native CP932 width path");
            int[] cjkX = { 10, 23, 36, 49 };
            finalStart = choiceGraphics.X.Count - cjkX.Length;
            for (int i = 0; i < cjkX.Length; i++)
                Equal(cjkX[i], choiceGraphics.X[finalStart + i], "pure CJK final-pass x at glyph " + i);

            // 23. Namae_nafuda is serialized through the game's CP932 writer. Swap
            //     only exact translated nameplate strings back to Japanese during
            //     SaveData, then restore the live Chinese array even after an error.
            canvas = new FakeCanvas();
            canvas.Namae_nafuda[1] = "(伊纲)";
            canvas.Namae_nafuda[2] = "不是姓名字段";
            object saveState = Harness.BeforeNativeSave(canvas);
            Equal("(伊綱)", canvas.Namae_nafuda[1], "native save receives CP932 name source");
            Equal("不是姓名字段", canvas.Namae_nafuda[2], "unmapped text is not treated as a name");
            Harness.AfterNativeSave(canvas, saveState);
            Equal("(伊纲)", canvas.Namae_nafuda[1], "live translated name restored after save");

            saveState = Harness.BeforeNativeSave(canvas);
            var saveError = new InvalidOperationException("save failed");
            Equal(saveError, Harness.FailedNativeSave(canvas, saveState, saveError),
                  "save finalizer preserves the native exception");
            Equal("(伊纲)", canvas.Namae_nafuda[1], "live translated name restored after failed save");

            // 24. The directly repaired native save contains complete Japanese
            //     source names, which translate exactly after load.
            canvas = new FakeCanvas();
            canvas.Namae_nafuda[0] = "(涼二)";
            canvas.Namae_nafuda[1] = "(伊綱)";
            canvas.Namae_nafuda[3] = "未收录姓名";
            canvas.Namae_nafuda[4] = "";
            Harness.AfterNativeLoad(canvas);
            Equal("(凉二)", canvas.Namae_nafuda[0], "Japanese save name translated after load");
            Equal("(伊纲)", canvas.Namae_nafuda[1], "complete Japanese save name translated after load");
            Equal("未收录姓名", canvas.Namae_nafuda[3], "unknown save name is untouched");
            Equal("", canvas.Namae_nafuda[4], "unused name slot remains empty");

            if (failures == 0) Console.WriteLine("PASS: ninth-game runtime substitution, nagasa, line state and in-line colour runs verified offline.");
            else throw new InvalidOperationException(failures + " runtime regression check(s) failed");
        }
    }
}
