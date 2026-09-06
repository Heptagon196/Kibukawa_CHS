using System;

namespace Kibu1ZhCN
{
    // Reuse original menu addresses to ask subject -> verb -> object in Chinese.
    // Each leaf still jumps to the original response for the same three choices.
    public static class SentencePuzzleLayout
    {
        private static readonly string[] Objects = { "电梯", "连接通道", "避难所" };
        private static readonly string[] Verbs = { "能变成", "不能变成" };

        private sealed class Node
        {
            internal readonly int Address, Opcode;
            internal readonly int[] OriginalTargets, Targets;
            internal Node(int address, int opcode, int[] originalTargets, int[] targets)
            {
                Address = address; Opcode = opcode;
                OriginalTargets = originalTargets; Targets = targets;
            }
        }

        private static readonly Node[] Nodes = {
            new Node(13992, 107, new[] {14027, 14048, 14069, 13967}, new[] {14027, 14048, 13967}),
            new Node(14027, 106, new[] {14188, 14309, 13992}, new[] {14188, 14441, 14626, 13992}),
            new Node(14048, 106, new[] {14441, 14536, 13992}, new[] {14309, 14536, 14626, 13992}),
            new Node(14090, 107, new[] {14125, 14146, 14167, 13967}, new[] {14125, 14146, 13967}),
            new Node(14125, 106, new[] {14906, 14909, 14090}, new[] {14906, 14992, 14626, 14090}),
            new Node(14146, 106, new[] {14992, 15103, 14090}, new[] {14909, 15103, 14626, 14090})
        };

        // Call after catalog translation, before the original menu starts executing.
        // No persistent state, scenario bytes, cursors, or saved offsets are changed.
        public static int Apply(string script, int instruction, int opcode, string[] labels, int[] targets)
        {
            if (script != "scn7" || labels == null || targets == null) return opcode;
            foreach (Node node in Nodes)
            {
                if (node.Address != instruction) continue;
                string[] before = node.Opcode == 107 ? Objects : Verbs;
                string[] after = node.Opcode == 107 ? Verbs : Objects;
                if (opcode != node.Opcode || labels.Length < Math.Max(before.Length, after.Length)
                    || targets.Length < Math.Max(node.OriginalTargets.Length, node.Targets.Length)) return opcode;
                for (int i = 0; i < before.Length; i++)
                    if (labels[i] != before[i]) return opcode;
                for (int i = 0; i < node.OriginalTargets.Length; i++)
                    if (targets[i] != node.OriginalTargets[i]) return opcode;

                Array.Clear(labels, 0, labels.Length);
                Array.Copy(after, labels, after.Length);
                // Only replace command arguments; retain the engine's scratch slots.
                Array.Copy(node.Targets, targets, node.Targets.Length);
                if (node.Targets.Length < node.OriginalTargets.Length)
                    targets[node.Targets.Length] = 65535;
                return after.Length + 104;
            }
            return opcode;
        }
    }
}
