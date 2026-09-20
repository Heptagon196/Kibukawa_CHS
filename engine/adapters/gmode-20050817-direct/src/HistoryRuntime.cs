using System;
using System.Collections;
using System.Collections.Generic;
using System.Reflection;
using BepInEx;
using HarmonyLib;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;

namespace KibukawaHistory
{
    public abstract class Gmode20050817DirectHistoryRuntime : HistoryView
    {
        protected virtual string TranslateSpeaker(string speaker) { return speaker; }
        private static Gmode20050817DirectHistoryRuntime self;
        private readonly DrawnHistoryTracker drawn = new DrawnHistoryTracker();
        private object drawnCanvas;
        private readonly HistoryAudioMute historyAudio = new HistoryAudioMute();
        private Harmony harmony;
        private object canvas;
        private UnityEngine.Object display;
        private Type displayType;
        private FieldInfo currentFrame, leftLabel, keypadState;
        private Text hintLabel;
        private SoftKeyHintState softHint = new SoftKeyHintState();
        private readonly HashSet<Type> canvasTypes = new HashSet<Type>();
        private readonly LeftSoftKeyInput leftSoftInput = new LeftSoftKeyInput();
        private int polledFrame = -1;
        private readonly ToggleInput toggleInput = new ToggleInput();
        private float previousScale;
        private int closedInputFrame = -1;
        private EventSystem events;
        private bool eventsEnabled;
        private static FieldInfo Field(object value, string name) { return AccessTools.Field(value.GetType(), name); }
        private static int Number(object value, string name) { return Convert.ToInt32(Field(value, name).GetValue(value)); }
        protected void InitializeHistory()
        {
            self = this;
            try
            {
                harmony = new Harmony(Info.Metadata.GUID);
                displayType = AccessTools.TypeByName("Socotra.UI.StDisplay");
                currentFrame = AccessTools.Field(displayType, "currentFrame");
                leftLabel = AccessTools.Field(displayType, "softKey1Label");
                keypadState = AccessTools.Field(displayType, "keypadState");
                if (currentFrame == null || leftLabel == null || keypadState == null) throw new MissingFieldException("StDisplay current frame/left label/keypad state");
                Patch(typeof(EventSystem), "Update", "BeforeInput", null);
                int count = 0;
                foreach (Type type in CanvasDiscovery.Resolve(AccessTools.TypeByName))
                {
                    canvasTypes.Add(type);
                    string name = type.FullName;
                    foreach (string field in new[] { "FrameTask", "MainTask", "Script", "BunsyouGun_gyousuu", "bg_itigyougun_mojiretu", "bg_itigyougun_color", "bg_itigyougun_control", "ColorTable", "NowNamae", "Namae_nafuda", "Namae_color", "command" })
                        if (AccessTools.Field(type, field) == null) throw new MissingFieldException(name, field);
                    var track=AccessTools.Field(type,"phraseTrack");
                    if(track==null || !track.FieldType.IsArray || AccessTools.Field(track.FieldType.GetElementType(),"audioSource")==null)
                        throw new MissingFieldException("History audio channel binding");
                    Patch(type, "BUNSYOU", null, "AfterText");
                    Patch(type, "DrawAdvString", null, "AfterDrawnCharacter");
                    Patch(type, "Run", null, "AfterScript");
                    Patch(type, "Game", "BeforeDirectScript", null);
                    Patch(type, "Game_adv", "BeforeDirectScript", null);
                    Patch(type, "Game_command", "BeforeDirectScript", null);
                    Patch(type, "ProcessEvent", "BeforeCanvasInput", null);
                    count++;
                }
                if (count == 0) throw new MissingMemberException("No supported CanvasEx");
                Patch(AccessTools.TypeByName("AppliArchive"), "Update", "BeforeArchiveUpdate", null);
                Logger.LogInfo("History ready: " + count + " unique canvas adapters; H / PageUp / native left softkey 21; 2000 session entries.");
            }
            catch (Exception error)
            {
                if (harmony != null) harmony.UnpatchSelf();
                enabled = false; self = null; Logger.LogError("History disabled: " + error);
            }
        }
        private void Patch(Type type, string name, string prefix, string postfix)
        {
            MethodInfo method = AccessTools.Method(type, name);
            if (method == null) throw new MissingMethodException(type == null ? "missing type" : type.FullName, name);
            var after = postfix == null ? null : new HarmonyMethod(typeof(Gmode20050817DirectHistoryRuntime), postfix) { priority = Priority.Last };
            harmony.Patch(method, prefix == null ? null : new HarmonyMethod(typeof(Gmode20050817DirectHistoryRuntime), prefix), after, null, null, null);
        }
        private bool RefreshSoftKeyHint()
        {
            if (display == null) display = UnityEngine.Object.FindObjectOfType(displayType);
            Text label = display == null ? null : leftLabel.GetValue(display) as Text;
            if (hintLabel != label)
            {
                RestoreSoftKeyHint();
                hintLabel = label;
                softHint = new SoftKeyHintState();
            }
            if (label == null) return false;
            object visible = currentFrame.GetValue(display);
            bool supported = visible != null && canvasTypes.Contains(visible.GetType());
            string inactive = supported ? String.Empty : null;
            bool available = supported && (open || (Time.timeScale > 0 && !Blocked));
            bool allowed = available && SoftKeyHintState.Allowed(softHint.Original(label.text), inactive);
            string caption = softHint.Render(label.text, available, inactive);
            if (label.text != caption) label.text = caption;
            if (supported) canvas = visible;
            return allowed;
        }
        private void RestoreSoftKeyHint()
        {
            if (hintLabel != null) hintLabel.text = softHint.Render(hintLabel.text, false, null);
        }
        // Read the actual label after game updates too: some game builds inline
        // their softkey setter. Never depend solely on a setter hook/cache.
        private void LateUpdate() { RefreshSoftKeyHint(); }
        private void Poll()
        {
            if (!Application.isFocused) return;
            bool keyboard = Input.GetKey(KeyCode.H) || Input.GetKey(KeyCode.PageUp);
            bool keyPressed = toggleInput.Pressed(Time.frameCount, keyboard);
            if (keyPressed)
            {
                if (open) Close();
                else OpenHistory();
            }
            // Sample input edges before game/UI handlers; scroll once per frame.
            if (polledFrame == Time.frameCount) return;
            polledFrame = Time.frameCount;
            if (open && Input.GetKeyDown(KeyCode.Escape)) Close();
            // StDisplay updates this before dispatching ProcessEvent. Read its
            // held state even while the history blocks delivery to the script.
            int navigation = 0;
            if (Blocked)
            {
                if (display == null) display = UnityEngine.Object.FindObjectOfType(displayType);
                if (display != null) navigation = (int)keypadState.GetValue(display);
            }
            if (Blocked) ClearKeys();
            if (open)
            {
                float direction = HistoryNavigation.Direction(Input.GetKey(KeyCode.UpArrow), Input.GetKey(KeyCode.DownArrow), navigation);
                scroll.y += direction * 520 * Mathf.Min(Time.unscaledDeltaTime, 0.05f);
                if (Input.GetKeyDown(KeyCode.End)) bottom = true;
                if (Input.GetKeyDown(KeyCode.Home)) scroll.y = 0;
            }
        }
        protected void TickHistory() { Poll(); }
        private void OpenHistory(bool fromSoftKey = false)
        {
            RefreshSoftKeyHint();
            if (canvas == null || display == null || !ReferenceEquals(currentFrame.GetValue(display), canvas) || Time.timeScale <= 0) return;
            // Native Play maps the text-sound channel to phraseTrack[1]; [0] is BGM.
            var tracks=(Array)Field(canvas,"phraseTrack").GetValue(null);
            object effect=tracks!=null && tracks.Length>1 ? tracks.GetValue(1) : null;
            historyAudio.Suspend(effect==null ? null : (AudioSource)Field(effect,"audioSource").GetValue(effect));
            open = true; bottom = true; openedFrame = Time.frameCount;
            previousScale = Time.timeScale; Time.timeScale = 0;
            events = EventSystem.current; eventsEnabled = events != null && events.enabled;
            if (events != null) events.enabled = false;
            ClearKeys();
        }
        private static bool BeforeCanvasInput(object __instance, int type, int param)
        {
            if (self == null) return true;
            self.Poll();
            bool pressed = self.leftSoftInput.Pressed(type, param);
            if (pressed && Application.isFocused)
            {
                if (self.open) { self.Close(); return false; }
                if (self.RefreshSoftKeyHint() && ReferenceEquals(__instance, self.canvas) && Time.timeScale > 0)
                {
                    self.OpenHistory(true);
                    return false;
                }
            }
            return !self.Blocked && Time.frameCount != self.closedInputFrame;
        }
        private void ClearKeys()
        {
            if (canvas == null) return;
            AccessTools.Method(canvas.GetType(), "KeyFlush").Invoke(canvas, null);
            foreach (FieldInfo field in canvas.GetType().GetFields(BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic))
                if (field.FieldType == typeof(int) && (field.Name.StartsWith("Key_", StringComparison.Ordinal) || field.Name.StartsWith("aKey_", StringComparison.Ordinal) || field.Name == "InputKey" || field.Name == "SavedKey" || field.Name == "KeyStatus")) field.SetValue(canvas, 0);
            FieldInfo skip = Field(canvas, "isPressSkipButton"); if (skip != null) skip.SetValue(canvas, false);
        }
        protected override void Close()
        {
            if (!open) return;
            historyAudio.Restore();
            open = false; Time.timeScale = previousScale;
            // Consume the closing input only in its delivery frame. A fresh
            // toggle press may reopen immediately; there is no cooldown.
            closedInputFrame = Time.frameCount;
            if (events != null) events.enabled = eventsEnabled;
            ClearKeys();
        }
        private static bool BeforeInput() { if (self == null) return true; self.Poll(); return !self.Blocked && Time.frameCount != self.closedInputFrame; }
        private static bool BeforeArchiveUpdate() { return BeforeInput(); }
        // Run remains a coroutine; Game/Game_adv/Game_command return bool in volume 10.
        private static bool BeforeDirectScript(object __instance, ref bool __result)
        {
            if (self == null) return true;
            self.canvas = __instance;
            if (!self.Blocked) return true;
            __result = true;
            return false;
        }
        private static void AfterScript(object __instance, ref IEnumerator __result)
        {
            if (self == null) return;
            self.canvas = __instance;
            __result = PausedEnumerator.Wrap(__result, delegate { return self != null && self.Blocked; });
        }
        // Starting a buffer does not disclose any of its still-hidden rows.
        private static void AfterText(object __instance)
        {
            if (self == null) return;
            self.canvas = __instance;
            if (Number(__instance,"MainTask")==17) return;
            self.drawnCanvas=__instance; self.drawn.Begin();
        }
        // DrawAdvString arguments: graphics, char index, slot index, row, x, y.
        // The renderer redraws visible characters every frame; dedupe by the
        // original row/character pair rather than by text or frame number.
        private static void AfterDrawnCharacter(object __instance,int __1,int __2,int __3)
        {
            if(self==null || !ReferenceEquals(self.drawnCanvas,__instance)) return;
            // PaintList shares DrawAdvString, but is never dialogue. Reject it
            // before speaker resolution: a prior dialogue's unvisited positions
            // otherwise repeat that expensive lookup on every notebook redraw.
            if(Number(__instance,"MainTask")==17) return;
            if(self.drawn.Seen(__3,__1)) return;
            string[] rows=(string[])Field(__instance,"bg_itigyougun_mojiretu").GetValue(__instance);
            sbyte[][] colors=(sbyte[][])Field(__instance,"bg_itigyougun_color").GetValue(__instance);
            if(__3<0 || __3>=rows.Length || rows[__3]==null || __1<0 || __1>=rows[__3].Length || __2<0 || __2>=colors[__3].Length) return;
            int[] palette=(int[])Field(__instance,"ColorTable").GetValue(__instance);
            int color=palette[(byte)colors[__3][__2]];
            string speaker=null;int speakerColor=color;
            int name=Number(__instance,"NowNamae");
            string[] names=(string[])Field(__instance,"Namae_nafuda").GetValue(__instance);
            if(name>=0 && name<names.Length)
            {
                speaker=names[name];
                speaker=self.TranslateSpeaker(speaker);
                int[] nameColors=(int[])Field(__instance,"Namae_color").GetValue(__instance);
                if(name<nameColors.Length) speakerColor=palette[nameColors[name]];
            }
            int terminal=0;
            if(__1==rows[__3].Length-1) {
                var controls=(sbyte[][])Field(__instance,"bg_itigyougun_control").GetValue(__instance);
                if(__3<controls.Length && controls[__3]!=null && __2<controls[__3].Length)terminal=(byte)controls[__3][__2];
            }
            self.drawn.Draw(self.history,__3,__1,rows[__3][__1],color,speaker,speakerColor,Number(__instance,"MainTask"),terminal);
        }
        protected void DisposeHistory()
        {
            Close(); RestoreSoftKeyHint(); if (harmony != null) harmony.UnpatchSelf();
            DisposeView(); if (self == this) self = null;
        }
    }
}
