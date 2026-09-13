using System;
using System.Collections.Generic;
using System.Reflection;
using BepInEx;
using HarmonyLib;
using UnityEngine;

namespace KibukawaHistory
{
    /// <summary>
    /// Dialogue history for the 20050117 VM (ninth title).
    ///
    /// The eighth game pauses by wrapping coroutine enumerators; this version has
    /// none at the top level: CanvasEx::Run loops ``result = Game(); yield return
    /// new WaitForFixedUpdate();``, so skipping Game() leaves the coroutine alive,
    /// stops every script advance and every input read for that frame, and keeps the
    /// last painted frame on screen. That is the whole pause mechanism.
    ///
    /// Capture happens where characters are actually drawn: CanvasEx::DrawAdvString
    /// is called once per revealed character with (graphics, keta, dan, x, y), so the
    /// history records exactly what the player has seen, never unread text. The
    /// renderer redraws visible characters every frame, so characters are deduped by
    /// their original (dan, keta) pair.
    /// </summary>
    public abstract class Gmode20050117HistoryRuntime : HistoryView
    {
        protected virtual string TranslateSpeaker(string speaker) { return speaker; }

        private static Gmode20050117HistoryRuntime self;
        private readonly DrawnTextHistory drawn = new DrawnTextHistory();
        private readonly HistoryAudioMute historyAudio = new HistoryAudioMute();
        private readonly ToggleInput toggleInput = new ToggleInput();
        private Harmony harmony;
        private Type canvasType;
        private object canvas;
        private object drawnCanvas;
        private float previousScale;
        private int polledFrame = -1;
        private int closedInputFrame = -1;

        private static readonly string[] RequiredFields = {
            "Bun_moji", "Bun_iro", "Bun_nagasa", "NowNamae", "Namae_nafuda", "Namae_color",
            "ColorTable", "phraseTrack", "MainTask"
        };

        private static FieldInfo Field(object value, string name)
        {
            FieldInfo field = AccessTools.Field(value.GetType(), name);
            if (field == null) throw new MissingFieldException(value.GetType().FullName, name);
            return field;
        }

        private static int Number(object value, string name) { return Convert.ToInt32(Field(value, name).GetValue(value)); }

        /// <summary>
        /// Handlers that clear the native character buffer, i.e. end an utterance.
        /// BUNSYOU_SLASH / BUNSYOU_SEMI_COLON only end a line inside the utterance, so
        /// they are deliberately not used here.
        /// </summary>
        private static readonly string[] BlockTerminators = { "BUNSYOU_PERIOD", "BUNSYOU_ASTARISK" };

        protected void InitializeHistory()
        {
            self = this;
            try
            {
                harmony = new Harmony(Info.Metadata.GUID);
                canvasType = AccessTools.TypeByName("CanvasEx");
                if (canvasType == null) throw new TypeLoadException("CanvasEx");
                foreach (string name in RequiredFields)
                    if (AccessTools.Field(canvasType, name) == null) throw new MissingFieldException(canvasType.FullName, name);
                Patch(canvasType, "Game", "BeforeGame", null);
                Patch(canvasType, "BUNSYOU", null, "AfterText");
                Patch(canvasType, "DrawAdvString", null, "AfterDrawnCharacter");
                // One BUNSYOU is one display line here. An utterance is the run of lines
                // up to the next handler that clears the native buffer, so Begin() per
                // utterance emits the speaker once, keeps the per-utterance draw dedupe,
                // and the last character of each line inserts the line break.
                foreach (string name in BlockTerminators)
                {
                    MethodInfo method = AccessTools.Method(canvasType, name);
                    if (method == null) throw new MissingMethodException(canvasType.FullName, name);
                    Patch(canvasType, name, null, "AfterLine");
                }
                Patch(canvasType, "LoadScenario", null, "AfterLoad");
                Patch(canvasType, "LoadScenarioEx", null, "AfterLoad");
                Logger.LogInfo("History ready: 20050117 canvas; H / PageUp toggle; 2000 session entries.");
            }
            catch (Exception error)
            {
                if (harmony != null) harmony.UnpatchSelf();
                enabled = false;
                self = null;
                Logger.LogError("History disabled: " + error);
            }
        }

        private void Patch(Type type, string name, string prefix, string postfix)
        {
            MethodInfo method = AccessTools.Method(type, name);
            if (method == null) throw new MissingMethodException(type.FullName, name);
            HarmonyMethod after = postfix == null ? null
                : new HarmonyMethod(typeof(Gmode20050117HistoryRuntime), postfix) { priority = Priority.Last };
            harmony.Patch(method, prefix == null ? null : new HarmonyMethod(typeof(Gmode20050117HistoryRuntime), prefix),
                          after, null, null, null);
        }

        /// <summary>Skip the whole frame while the overlay owns input, without ending the coroutine.</summary>
        protected static bool BeforeGame(object __instance, ref bool __result)
        {
            if (self == null || !self.Blocked || Time.frameCount == self.closedInputFrame) return true;
            self.canvas = __instance;
            __result = true;                 // CanvasEx::Run keeps looping when Game() reports true
            return false;                    // do not run the original
        }

        /// <summary>A BUNSYOU fragment is stocked; remember which canvas is drawing.</summary>
        protected static void AfterText(object __instance)
        {
            if (self == null) return;
            self.canvas = __instance;
            self.drawnCanvas = __instance;
        }

        /// <summary>The block ended: the next block starts a fresh history entry.</summary>
        protected static void AfterLine(object __instance)
        {
            if (self == null) return;
            self.drawn.Begin();
        }

        /// <summary>A fresh script must not inherit the previous block's dedupe set.</summary>
        protected static void AfterLoad(object __instance)
        {
            if (self == null) return;
            self.canvas = __instance;
            self.drawn.Begin();
        }

        /// <summary>
        /// DrawAdvString(graphics, keta, dan, x, y) draws one revealed character from
        /// Bun_moji[dan] with the colour in Bun_iro[dan][keta].
        /// </summary>
        protected static void AfterDrawnCharacter(object __instance, int __1, int __2)
        {
            if (self == null || !ReferenceEquals(self.drawnCanvas, __instance)) return;
            if (self.drawn.Seen(__2, __1)) return;
            string[] lines = (string[])Field(__instance, "Bun_moji").GetValue(__instance);
            if (lines == null || __2 < 0 || __2 >= lines.Length) return;
            string line = lines[__2];
            if (line == null || __1 < 0 || __1 >= line.Length) return;
            int[][] colors = (int[][])Field(__instance, "Bun_iro").GetValue(__instance);
            int[] palette = (int[])Field(__instance, "ColorTable").GetValue(__instance);
            int color = Palette(palette, colors, __2, __1);
            string speaker = null;
            int speakerColor = color;
            string[] names = (string[])Field(__instance, "Namae_nafuda").GetValue(__instance);
            int name = Number(__instance, "NowNamae");
            if (names != null && name >= 0 && name < names.Length && !String.IsNullOrEmpty(names[name]))
            {
                speaker = self.TranslateSpeaker(names[name]);
                int[] nameColors = (int[])Field(__instance, "Namae_color").GetValue(__instance);
                if (nameColors != null && name < nameColors.Length) speakerColor = Palette(palette, nameColors[name]);
            }
            // The line ends at its last character; there is no control plane in this VM.
            int[] lengths = (int[])Field(__instance, "Bun_nagasa").GetValue(__instance);
            bool last = lengths != null && __2 < lengths.Length && lengths[__2] > 0 && __1 == lengths[__2] - 1;
            self.drawn.Draw(self.history, __2, __1, line[__1], color, speaker, speakerColor, last);
        }

        private static int Palette(int[] palette, int[][] colors, int row, int slot)
        {
            if (colors == null || row < 0 || row >= colors.Length || colors[row] == null) return 0xffffff;
            if (slot < 0 || slot >= colors[row].Length) return 0xffffff;
            int index = colors[row][slot];
            if (palette == null || index < 0 || index >= palette.Length) return 0xffffff;
            return palette[index] & 0xffffff;
        }

        private static int Palette(int[] palette, int index)
        {
            if (palette == null || index < 0 || index >= palette.Length) return 0xffffff;
            return palette[index] & 0xffffff;
        }

        protected void TickHistory() { Poll(); }

        private void Poll()
        {
            if (!Application.isFocused) return;
            bool keyboard = Input.GetKey(KeyCode.H) || Input.GetKey(KeyCode.PageUp);
            if (toggleInput.Pressed(Time.frameCount, keyboard))
            {
                if (open) Close();
                else OpenHistory();
            }
            if (polledFrame == Time.frameCount) return;
            polledFrame = Time.frameCount;
            if (open && Input.GetKeyDown(KeyCode.Escape)) Close();
            if (!open) return;
            float direction = HistoryNavigation.Direction(Input.GetKey(KeyCode.UpArrow), Input.GetKey(KeyCode.DownArrow), 0);
            scroll.y += direction * 520 * Mathf.Min(Time.unscaledDeltaTime, 0.05f);
            if (Input.GetKeyDown(KeyCode.End)) bottom = true;
            if (Input.GetKeyDown(KeyCode.Home)) scroll.y = 0;
        }

        private void OpenHistory()
        {
            if (canvas == null || Time.timeScale <= 0) return;
            // Play maps the text channel to phraseTrack[1]; [0] is music.
            Array tracks = (Array)Field(canvas, "phraseTrack").GetValue(null);
            object effect = tracks != null && tracks.Length > 1 ? tracks.GetValue(1) : null;
            historyAudio.Suspend(effect == null ? null : (AudioSource)Field(effect, "audioSource").GetValue(effect));
            open = true;
            bottom = true;
            openedFrame = Time.frameCount;
            previousScale = Time.timeScale;
            Time.timeScale = 0;
            ClearKeys();
        }

        protected override void Close()
        {
            if (!open) return;
            historyAudio.Restore();
            open = false;
            Time.timeScale = previousScale;
            // Swallow only the frame that delivered the closing input.
            closedInputFrame = Time.frameCount;
            ClearKeys();
        }

        private void ClearKeys()
        {
            if (canvas == null) return;
            MethodInfo flush = AccessTools.Method(canvas.GetType(), "KeyFlush");
            if (flush != null) flush.Invoke(canvas, null);
            foreach (FieldInfo field in canvas.GetType().GetFields(BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic))
                if (field.FieldType == typeof(int) && (field.Name.StartsWith("Key_", StringComparison.Ordinal)
                    || field.Name.StartsWith("aKey_", StringComparison.Ordinal)
                    || field.Name == "InputKey" || field.Name == "SavedKey" || field.Name == "KeyStatus"))
                    field.SetValue(canvas, 0);
        }

        protected void DisposeHistory()
        {
            Close();
            if (harmony != null) harmony.UnpatchSelf();
            DisposeView();
            if (self == this) self = null;
        }
    }
}
