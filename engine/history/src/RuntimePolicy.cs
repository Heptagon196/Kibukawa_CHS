using System;
using System.Collections.Generic;

namespace KibukawaHistory
{
    public static class HistoryNavigation
    {
        public static int Direction(bool keyboardUp, bool keyboardDown, int gameKeypadState)
        {
            bool up = keyboardUp || (gameKeypadState & (1 << 17)) != 0;
            bool down = keyboardDown || (gameKeypadState & (1 << 19)) != 0;
            return (down ? 1 : 0) - (up ? 1 : 0);
        }
        public static bool Held(int state) { return (state & ((1 << 17) | (1 << 19))) != 0; }
    }
    public sealed class LeftSoftKeyInput
    {
        public bool Held { get; private set; }
        public bool Pressed(int eventType, int key)
        {
            if (key != 21) return false;
            if (eventType == 2) { Held = false; return false; }
            if (eventType != 1) return false;
            bool pressed = !Held;
            Held = true;
            return pressed;
        }
    }
    public sealed class LeftSoftKeyHint
    {
        public const string Caption = "历史记录";
        private string original;
        private bool replaced;
        public string Original(string current)
        {
            if (!replaced || current != Caption) { original = current; replaced = false; }
            return original;
        }
        public static bool Allowed(string label, string inactiveLabel)
        {
            return !string.IsNullOrEmpty(inactiveLabel) && label == inactiveLabel;
        }
        public string Render(string current, bool available, string inactiveLabel)
        {
            string source = Original(current);
            replaced = available && Allowed(source, inactiveLabel);
            return replaced ? Caption : source;
        }
    }
    public static class CanvasDiscovery
    {
        public static IEnumerable<Type> Resolve(Func<string, Type> lookup)
        {
            var seen = new HashSet<Type>();
            foreach (string name in new[] { "CanvasEx", "appli1.CanvasEx", "appli2.CanvasEx" })
            {
                Type type = lookup(name);
                // Harmony also resolves short names. "CanvasEx" can be the
                // exact same Type as "appli1.CanvasEx" in volumes 4 and 5.
                if (type != null && seen.Add(type)) yield return type;
            }
        }
    }
    public sealed class ToggleInput
    {
        private int pressedFrame = -1;
        private bool held;
        public bool Pressed(int currentFrame, bool down)
        {
            bool pressed = down && !held && pressedFrame != currentFrame;
            held = down;
            if (pressed) pressedFrame = currentFrame;
            return pressed;
        }
    }
}
