using System;
using System.IO;
using BepInEx;
using UnityEngine;
using UnityEngine.UI;

namespace Kibu6ZhCN
{
    [BepInPlugin("local.kibu6.reference", "Kibu6 Knowledge Reference", "0.1.0")]
    [BepInProcess("kibu6.exe")]
    public sealed class ReferencePlugin : BaseUnityPlugin
    {
        private GameObject root;
        private Font font;

        private void Start()
        {
            // Independent UI: no game assets, input bindings or adapters changed.
            root = new GameObject("Kibu6KnowledgeSidebar", typeof(RectTransform),
                typeof(Canvas), typeof(CanvasScaler), typeof(GraphicRaycaster));
            DontDestroyOnLoad(root);
            var canvas = root.GetComponent<Canvas>();
            canvas.renderMode = RenderMode.ScreenSpaceOverlay;
            canvas.sortingOrder = 100;
            var scaler = root.GetComponent<CanvasScaler>();
            scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
            scaler.referenceResolution = new Vector2(1280, 720);
            scaler.matchWidthOrHeight = 0.5f;

            var go = new GameObject("KnowledgeButton", typeof(RectTransform), typeof(Image), typeof(Button));
            go.transform.SetParent(root.transform, false);
            var rect = go.GetComponent<RectTransform>();
            rect.anchorMin = rect.anchorMax = rect.pivot = new Vector2(1, 0);
            rect.anchoredPosition = new Vector2(-24, 96);
            rect.sizeDelta = new Vector2(144, 44);
            go.GetComponent<Image>().color = new Color(0.10f, 0.16f, 0.21f, 0.96f);
            var button = go.GetComponent<Button>();
            button.targetGraphic = go.GetComponent<Image>();
            // Do not enter the game's controller/keyboard navigation sequence.
            button.navigation = new Navigation { mode = Navigation.Mode.None };
            button.onClick.AddListener(OpenReference);

            var label = new GameObject("Label", typeof(RectTransform), typeof(Text));
            label.transform.SetParent(go.transform, false);
            var lr = label.GetComponent<RectTransform>();
            lr.anchorMin = Vector2.zero; lr.anchorMax = Vector2.one;
            lr.offsetMin = lr.offsetMax = Vector2.zero;
            font = Font.CreateDynamicFontFromOSFont(new[] { "Microsoft YaHei", "SimHei", "Arial" }, 20);
            var text = label.GetComponent<Text>();
            text.font = font; text.fontSize = 20; text.text = "知识参考 ↗";
            text.alignment = TextAnchor.MiddleCenter; text.color = Color.white;
            text.raycastTarget = false;
        }

        private void OpenReference()
        {
            var path = Path.Combine(Path.GetDirectoryName(Info.Location), "reference.html");
            if (!File.Exists(path))
            {
                Logger.LogError("Missing knowledge reference: " + path);
                return;
            }
            // Fixed bundled file only; no remote requests or shell commands.
            Application.OpenURL(new Uri(Path.GetFullPath(path)).AbsoluteUri);
        }

        private void OnDestroy()
        {
            if (root != null) Destroy(root);
            if (font != null) Destroy(font);
        }
    }
}
