using System;
using System.Collections.Generic;
using BepInEx;
using UnityEngine;
namespace KibukawaHistory
{
    public abstract class HistoryView : BaseUnityPlugin
    {
        protected readonly HistoryBuffer history = new HistoryBuffer(2000);
        protected bool open;
        protected int openedFrame = -1;
        protected Vector2 scroll;
        protected bool bottom;
        protected Font font;
        protected GUIStyle body, heading, hint, closeButton;
        protected readonly List<float> heights = new List<float>();
        protected readonly List<ColoredHistoryLayout> coloredLines = new List<ColoredHistoryLayout>();
        protected readonly Dictionary<char, float> advances = new Dictionary<char, float>();
        protected float contentHeight, layoutWidth;
        protected int layoutVersion = -1;
        protected bool Blocked { get { return open; } }
        protected abstract void Close();
        protected void DisposeView() { if(font!=null) Destroy(font); }
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
        protected void DrawHistory()
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
    }
}
