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
    [BepInPlugin("local.kibukawa.history", "Kibukawa Dialogue History", "1.6.2")]
    [BepInProcess("kibu1.exe"), BepInProcess("kibu2.exe"), BepInProcess("kibu3.exe"), BepInProcess("kibu4.exe"), BepInProcess("kibu5.exe"), BepInProcess("kibu6.exe")]
    public sealed class HistoryPlugin : BaseUnityPlugin
    {
        private static HistoryPlugin self;
        private readonly HistoryBuffer history = new HistoryBuffer(2000);
        private Harmony harmony;
        private object canvas;
        private bool open;
        private UnityEngine.Object display;
        private Type displayType;
        private FieldInfo currentFrame, leftLabel, keypadState;
        private Text hintLabel;
        private LeftSoftKeyHint softHint = new LeftSoftKeyHint();
        private readonly HashSet<Type> canvasTypes = new HashSet<Type>();
        private readonly LeftSoftKeyInput leftSoftInput = new LeftSoftKeyInput();
        private int openedFrame = -1;
        private int polledFrame = -1;
        private readonly ToggleInput toggleInput = new ToggleInput();
        private float previousScale;
        private int closedInputFrame = -1;
        private EventSystem events;
        private bool eventsEnabled;
        private Vector2 scroll;
        private bool bottom;
        private Font font;
        private GUIStyle body, heading, hint, closeButton;
        private readonly List<float> heights = new List<float>();
        private readonly List<ColoredHistoryLayout> coloredLines = new List<ColoredHistoryLayout>();
        private readonly Dictionary<char, float> advances = new Dictionary<char, float>();
        private float contentHeight, layoutWidth;
        private int layoutVersion = -1;
        private static FieldInfo Field(object value, string name) { return AccessTools.Field(value.GetType(), name); }
        private static int Number(object value, string name) { return Convert.ToInt32(Field(value, name).GetValue(value)); }
        private bool Blocked { get { return open; } }
        private void Awake()
        {
            self = this;
            try
            {
                harmony = new Harmony("local.kibukawa.history");
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
                    foreach (string field in new[] { "Scene", "Cmd", "Key", "KeyS", "TextPos", "TextLen", "TextC", "scColor", "Truth", "command" })
                        if (AccessTools.Field(type, field) == null) throw new MissingFieldException(name, field);
                    Patch(type, "ExeText", "BeforeText", "AfterText");
                    Patch(type, "Script", null, "AfterScript");
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
            var after = postfix == null ? null : new HarmonyMethod(typeof(HistoryPlugin), postfix) { priority = Priority.Last };
            harmony.Patch(method, prefix == null ? null : new HarmonyMethod(typeof(HistoryPlugin), prefix), after);
        }
        private bool RefreshSoftKeyHint()
        {
            if (display == null) display = UnityEngine.Object.FindObjectOfType(displayType);
            Text label = display == null ? null : leftLabel.GetValue(display) as Text;
            if (hintLabel != label)
            {
                RestoreSoftKeyHint();
                hintLabel = label;
                softHint = new LeftSoftKeyHint();
            }
            if (label == null) return false;
            object visible = currentFrame.GetValue(display);
            bool supported = visible != null && canvasTypes.Contains(visible.GetType());
            string inactive = supported ? ((string[])Field(visible, "command").GetValue(null))[0] : null;
            bool available = supported && (open || (Time.timeScale > 0 && !Blocked));
            bool allowed = available && LeftSoftKeyHint.Allowed(softHint.Original(label.text), inactive);
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
        private void Update() { Poll(); }
        private void OpenHistory(bool fromSoftKey = false)
        {
            if (canvas == null || (!fromSoftKey && Number(canvas, "Scene") != 2) || Time.timeScale <= 0) return;
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
            foreach (string field in new[] { "Key", "KeyS" })
            {
                Array keys = (Array)Field(canvas, field).GetValue(canvas); Array.Clear(keys, 0, keys.Length);
            }
            AccessTools.Method(canvas.GetType(), "ClearKey").Invoke(canvas, null);
            FieldInfo skip = Field(canvas, "isPressSkipButton"); if (skip != null) skip.SetValue(canvas, false);
        }
        private void Close()
        {
            if (!open) return;
            open = false; Time.timeScale = previousScale;
            // Consume the closing input only in its delivery frame. A fresh
            // toggle press may reopen immediately; there is no cooldown.
            closedInputFrame = Time.frameCount;
            if (events != null) events.enabled = eventsEnabled;
            ClearKeys();
        }
        private static bool BeforeInput() { if (self == null) return true; self.Poll(); return !self.Blocked && Time.frameCount != self.closedInputFrame; }
        private static bool BeforeArchiveUpdate() { return BeforeInput(); }
        private static void AfterScript(object __instance, ref IEnumerator __result)
        {
            if (self == null) return;
            self.canvas = __instance;
            __result = PausedEnumerator.Wrap(__result, delegate { return self != null && self.Blocked; });
        }
        private static void BeforeText(object __instance, out int __state)
        {
            var pos = (sbyte[])Field(__instance, "TextPos").GetValue(__instance);
            __state = ((sbyte[])Field(__instance, "TextLen").GetValue(__instance))[pos[0]];
        }
        private static void AfterText(object __instance, string Str, int Type, int __state)
        {
            if (self == null || Number(__instance, "Scene") != 2) return;
            self.canvas = __instance;
            int cmd = Number(__instance, "Cmd");
            if (Str == null)
            {
                if (Type == 1 || Type == 2 || Type == 3 || (Type == 0 && cmd == 71)) self.history.Break();
                return;
            }
            if (cmd != 71 && cmd != 72 && cmd != 82 && cmd != 83) return;
            var pos = (sbyte[])Field(__instance, "TextPos").GetValue(__instance);
            int added = ((sbyte[])Field(__instance, "TextLen").GetValue(__instance))[pos[0]] - __state;
            if (added > 0)
            {
                int count = Math.Min(added, Str.Length);
                sbyte[] rowColors = ((sbyte[][])Field(__instance, "TextC").GetValue(__instance))[pos[0]];
                int[] palette = (int[])Field(__instance, "scColor").GetValue(__instance);
                var colors = new int[count];
                for (int i = 0; i < count; i++) colors[i] = palette[rowColors[__state + i]] & 0xFFFFFF;
                self.history.Append(Str.Substring(0, count), colors);
            }
        }
        private float MeasureCharacter(char c)
        {
            float value;
            if (!advances.TryGetValue(c, out value))
            {
                value = body.CalcSize(new GUIContent(c.ToString())).x;
                advances.Add(c, value);
            }
            return value;
        }
        private void OnGUI()
        {
            if (!open) return;
            if (body == null)
            {
                font = Font.CreateDynamicFontFromOSFont(new[] { "Microsoft YaHei", "SimSun", "Noto Sans CJK SC" }, 24);
                body = new GUIStyle(GUI.skin.label) { font = font, fontSize = 24, wordWrap = false, richText = false, padding = new RectOffset(0, 0, 0, 0) };
                body.normal.textColor = Color.white;
                heading = new GUIStyle(body) { fontSize = 30 };
                hint = new GUIStyle(body) { fontSize = 17 };
                closeButton = new GUIStyle(GUI.skin.button) { font = font, fontSize = 20 };
            }
            bool oldEnabled = GUI.enabled;
            GUI.enabled = oldEnabled && Time.frameCount != openedFrame;
            Matrix4x4 oldMatrix = GUI.matrix;
            int oldDepth = GUI.depth;
            float scale = Mathf.Max(0.1f, Mathf.Min(Screen.width / 1100f, Screen.height / 760f));
            float width = Screen.width / scale, height = Screen.height / scale;
            GUI.matrix = Matrix4x4.Scale(new Vector3(scale, scale, 1)); GUI.depth = -10000;
            Color oldColor = GUI.color;
            GUI.color = new Color(0.045f, 0.055f, 0.07f, 0.98f);
            GUI.DrawTexture(new Rect(0, 0, width, height), Texture2D.whiteTexture); GUI.color = oldColor;
            float left = Mathf.Max(36, (width - 1040) / 2), panelWidth = width - left * 2;
            GUI.Label(new Rect(left, 24, panelWidth - 140, 48), "历史记录", heading);
            if (GUI.Button(new Rect(width - left - 110, 29, 110, 38), "关闭", closeButton)) Close();
            GUI.Label(new Rect(left, height - 49, panelWidth, 35), "L 提示历史记录时打开　 H / PageUp 开关　 ↑↓ / 摇杆 / 滚轮 浏览", hint);
            // A fixed panel contains both the text viewport and its scrollbar.
            // Insets keep the first/last rows away from the visible border.
            Rect panel = new Rect(left, 91, panelWidth, height - 158);
            GUI.color = new Color(0.43f, 0.48f, 0.53f, 1f);
            GUI.DrawTexture(panel, Texture2D.whiteTexture);
            GUI.color = new Color(0.07f, 0.085f, 0.105f, 1f);
            GUI.DrawTexture(new Rect(panel.x + 2, panel.y + 2, panel.width - 4, panel.height - 4), Texture2D.whiteTexture);
            GUI.color = oldColor;
            Rect viewport = new Rect(panel.x + 20, panel.y + 18, panel.width - 40, panel.height - 36);
            float textWidth = viewport.width - 34;
            if (layoutVersion != history.Version || layoutWidth != textWidth)
            {
                heights.Clear(); coloredLines.Clear(); contentHeight = 0;
                for (int i = 0; i < history.Entries.Count; i++)
                {
                    var layout = new ColoredHistoryLayout(history.Entries[i], history.Colors[i], textWidth, body.lineHeight + 4, MeasureCharacter);
                    coloredLines.Add(layout);
                    float h = layout.Height + 18;
                    heights.Add(h); contentHeight += h;
                }
                layoutWidth = textWidth; layoutVersion = history.Version;
            }
            if (bottom) { scroll.y = Mathf.Max(0, contentHeight - viewport.height); bottom = false; }
            scroll.y = Mathf.Clamp(scroll.y, 0, Mathf.Max(0, contentHeight - viewport.height));
            scroll = GUI.BeginScrollView(viewport, scroll, new Rect(0, 0, textWidth, Mathf.Max(viewport.height, contentHeight)));
            float y = 0;
            if (heights.Count == 0) GUI.Label(new Rect(0, 12, textWidth, 70), "暂无记录。继续剧情后，已显示的文本会保存在这里。", body);
            for (int i = 0; i < heights.Count; i++)
            {
                if (y + heights[i] >= scroll.y && y <= scroll.y + viewport.height)
                    foreach (ColoredHistoryLayout.Run run in coloredLines[i].Runs)
                    {
                        GUI.color = new Color(((run.Color >> 16) & 255) / 255f, ((run.Color >> 8) & 255) / 255f, (run.Color & 255) / 255f, 1f);
                        GUI.Label(new Rect(run.X, y + run.Y, textWidth - run.X + 2, body.lineHeight + 4), run.Text, body);
                    }
                y += heights[i];
            }
            GUI.color = oldColor;
            GUI.EndScrollView();
            GUI.matrix = oldMatrix; GUI.depth = oldDepth; GUI.enabled = oldEnabled;
        }
        private void OnDestroy()
        {
            Close(); RestoreSoftKeyHint(); if (harmony != null) harmony.UnpatchSelf();
            if (font != null) Destroy(font); if (self == this) self = null;
        }
    }
}
