using System;
using System.Collections;
using System.Collections.Generic;

namespace KibukawaHistory
{
    public sealed class HistoryBuffer
    {
        public readonly List<string> Entries = new List<string>();
        public readonly List<List<int>> Colors = new List<List<int>>();
        private readonly int capacity;
        private bool boundary = true;
        public int Version { get; private set; }
        public HistoryBuffer(int capacity) { this.capacity = Math.Max(1, capacity); }
        public void Break() { boundary = true; }
        public void Append(string text)
        {
            if (text == null) return;
            var colors = new int[text.Length];
            for (int i = 0; i < colors.Length; i++) colors[i] = 0xFFFFFF;
            Append(text, colors);
        }
        public void Append(string text, int[] colors)
        {
            if (string.IsNullOrEmpty(text)) return;
            if (colors == null || colors.Length != text.Length) throw new ArgumentException("One RGB value per character is required");
            // Bound both entry count and individual entry size, even for scripts
            // that never emit a wait or a clear.
            for (int i = 0; i < text.Length; i++)
            {
                if (boundary || Entries.Count == 0 || Entries[Entries.Count - 1].Length >= 2000)
                {
                    Entries.Add(""); boundary = false;
                    Colors.Add(new List<int>());
                    if (Entries.Count > capacity) { Entries.RemoveAt(0); Colors.RemoveAt(0); }
                }
                Entries[Entries.Count - 1] += text[i];
                Colors[Colors.Count - 1].Add(colors[i] & 0xFFFFFF);
            }
            Version++;
        }
    }

    public static class PausedEnumerator
    {
        // Gate nested iterators too: setting timeScale alone cannot stop a
        // coroutine which is already inside a dialogue's input/typewriter loop.
        public static IEnumerator Wrap(IEnumerator original, Func<bool> paused)
        {
            try
            {
                while (true)
                {
                    while (paused()) yield return null;
                    if (!original.MoveNext()) yield break;
                    IEnumerator nested = original.Current as IEnumerator;
                    yield return nested == null ? original.Current : Wrap(nested, paused);
                }
            }
            finally
            {
                IDisposable disposable = original as IDisposable;
                if (disposable != null) disposable.Dispose();
            }
        }
    }
}
