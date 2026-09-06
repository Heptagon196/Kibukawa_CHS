using System;
using UnityEngine;
using UnityEngine.UI;

namespace Kibu1ZhCN
{
    // Help pages are sprites, not UI.Text. Rebuild their content as scalable UI;
    // the original dialog continues to own input, page count, arrows and closing.
    public sealed class HelpPageView : MonoBehaviour
    {
        public const string TextPrefix = "Kibu1ZhCN.Help";
        private RectTransform content;
        private string shown;
        private const float Width = 930, Height = 632;
        private static readonly Color Blue = new Color32(5, 29, 88, 255);

        public void Show(string spriteName, Font font)
        {
            HelpPage page = HelpPages.Find(spriteName);
            if (page == null || font == null)
            {
                if (content != null) content.gameObject.SetActive(false);
                shown = null;
                return;
            }
            if (shown == spriteName && content != null)
            {
                content.gameObject.SetActive(true);
                Fit();
                return;
            }
            if (content != null)
            {
                content.gameObject.SetActive(false);
                Destroy(content.gameObject);
            }
            var root = new GameObject("Kibu1ZhCN Help Page", typeof(RectTransform));
            root.SetActive(false);
            content = (RectTransform)root.transform;
            content.SetParent(transform, false);
            content.anchorMin = content.anchorMax = content.pivot = new Vector2(.5f, .5f);
            content.sizeDelta = new Vector2(Width, Height);
            // The original rounded frame is drawn by the dialog behind Guide.
            // Leave its 12px perimeter visible while covering baked Japanese text.
            Box("Background", 12, 12, Width-24, Height-24, Blue);
            Label("Title", page.Title, 28, 24, 874, 45, 32, Color.white, TextAnchor.MiddleCenter, font, true);
            if (page.Rows != null)
            {
                Label("Subtitle", page.Subtitle, 30, 77, 870, 45, 23, Color.white, TextAnchor.MiddleCenter, font, true);
                for (int i = 0; i < page.Rows.Length; i++)
                {
                    float y = 140 + i * 64;
                    Box("Key background", 30, y, 430, 59, new Color32(91,105,149,255));
                    Box("Action background", 460, y, 440, 59, new Color32(181,186,206,255));
                    Label("Key" + i, page.Rows[i][0], 45, y+4, 403, 51, 25, Color.white, TextAnchor.MiddleLeft, font, true);
                    Label("Action" + i, page.Rows[i][1], 476, y+4, 408, 51, 25, Color.black, TextAnchor.MiddleLeft, font, true);
                }
                Label("Footer", page.Footer, 42, 547, 846, 68, 22, Color.white, TextAnchor.MiddleCenter, font, true);
            }
            else
            {
                Label("Body", page.Body, 60, 112, 810, 464, 26, Color.white, TextAnchor.UpperLeft, font, true);
            }
            shown = spriteName;
            Fit();
            root.SetActive(true);
        }

        private RectTransform Rect(string name, float x, float y, float width, float height)
        {
            var obj = new GameObject(TextPrefix + "." + name, typeof(RectTransform));
            obj.SetActive(false);
            var rect = (RectTransform)obj.transform;
            rect.SetParent(content, false);
            rect.anchorMin = rect.anchorMax = rect.pivot = new Vector2(0, 1);
            rect.anchoredPosition = new Vector2(x, -y);
            rect.sizeDelta = new Vector2(width, height);
            return rect;
        }
        private void Box(string name, float x, float y, float width, float height, Color color)
        {
            var rect = Rect(name, x, y, width, height);
            var image = rect.gameObject.AddComponent<Image>();
            image.color = color;
            image.raycastTarget = false;
            rect.gameObject.SetActive(true);
        }
        private void Label(string name, string value, float x, float y, float width, float height,
            int size, Color color, TextAnchor alignment, Font font, bool bold)
        {
            var rect = Rect(name, x, y, width, height);
            var text = rect.gameObject.AddComponent<Text>();
            text.font = font;
            text.fontSize = size;
            text.fontStyle = bold ? FontStyle.Bold : FontStyle.Normal;
            text.lineSpacing = 1.18f;
            text.alignment = alignment;
            text.color = color;
            text.horizontalOverflow = HorizontalWrapMode.Wrap;
            text.verticalOverflow = VerticalWrapMode.Truncate;
            text.resizeTextForBestFit = true;
            text.resizeTextMinSize = size - 3;
            text.resizeTextMaxSize = size;
            text.supportRichText = false;
            text.raycastTarget = false;
            text.text = value ?? "";
            rect.gameObject.SetActive(true);
        }
        private void LateUpdate() { Fit(); }
        private void Fit()
        {
            if (content == null) return;
            var parent = transform as RectTransform;
            if (parent == null || parent.rect.width <= 0 || parent.rect.height <= 0) return;
            content.localScale = new Vector3(parent.rect.width/Width, parent.rect.height/Height, 1);
        }
    }
}
