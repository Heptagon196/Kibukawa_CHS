using System;
using System.Linq;
using HarmonyLib;
using KibukawaHistory;
// Reproduce Harmony's real short-name fallback with a namespaced-only canvas.
namespace appli1 { public class CanvasEx {} }
class RuntimePolicyTests
{
    static int Main()
    {
        int failures = 0;
        if (HistoryNavigation.Direction(false,false,1<<17) != -1 ||
            HistoryNavigation.Direction(false,false,1<<19) != 1 ||
            HistoryNavigation.Direction(true,false,1<<17) != -1 ||
            HistoryNavigation.Direction(false,false,(1<<17)|(1<<19)) != 0 ||
            HistoryNavigation.Direction(false,false,1<<21) != 0 ||
            HistoryNavigation.Direction(false,false,0) != 0 ||
            !HistoryNavigation.Held((1<<17)|(1<<19)) || HistoryNavigation.Held(0)) failures++;
        if (failures == 0) Console.WriteLine("PASS game held navigation: up/down, release, conflicting directions, keyboard merge and close-input isolation");
        var soft = new LeftSoftKeyInput();
        if (!soft.Pressed(1,21) || soft.Pressed(1,21) || !soft.Held) failures++;
        if (soft.Pressed(2,21) || soft.Held || !soft.Pressed(1,21)) failures++;
        if (soft.Pressed(1,22) || soft.Pressed(1,20) || soft.Pressed(1,17)) failures++;
        if (failures == 0) Console.WriteLine("PASS native left softkey 21: press/release/repress; held, right softkey and other keys excluded");
        var hint = new LeftSoftKeyHint();
        if (hint.Render("---", true, "---") != LeftSoftKeyHint.Caption ||
            hint.Original(LeftSoftKeyHint.Caption) != "---" ||
            hint.Render(LeftSoftKeyHint.Caption, true, "---") != LeftSoftKeyHint.Caption ||
            hint.Render("返回", true, "---") != "返回" ||
            LeftSoftKeyHint.Allowed(hint.Original("返回"), "---") ||
            hint.Render("---", true, "---") != LeftSoftKeyHint.Caption ||
            hint.Render(LeftSoftKeyHint.Caption, false, "---") != "---" ||
            hint.Render("", true, "---") != "" ||
            hint.Render(null, true, "---") != null ||
            LeftSoftKeyHint.Allowed(null, null) ||
            LeftSoftKeyHint.Allowed("", "") ||
            hint.Render("历史记录", true, "---") != "历史记录" ||
            LeftSoftKeyHint.Allowed(hint.Original("历史记录"), "---")) failures++;
        if (failures == 0) Console.WriteLine("PASS idle L hint: replace, preserve original, repeat, active action, restore, unknown and unowned caption");
        var types = CanvasDiscovery.Resolve(AccessTools.TypeByName).ToArray();
        var log = new HistoryBuffer(10);
        // One native text call, one postfix for every discovered adapter.
        foreach (Type type in types) log.Append("尾场");
        if (log.Entries.Single() != "尾场")
        { Console.WriteLine("FAIL native text called once, history = " + log.Entries.Single() + "; adapters=" + types.Length); failures++; }
        else Console.WriteLine("PASS one text hook for namespaced canvas");
        var key = new ToggleInput();
        key.Pressed(10, false); // Plugin Update before input delivery.
        if (!key.Pressed(10, true)) // Game queries input later in same frame.
        { Console.WriteLine("FAIL late input press lost in same frame"); failures++; }
        else Console.WriteLine("PASS late input press captured");
        if (key.Pressed(11, true)) { Console.WriteLine("FAIL holding key toggles twice"); failures++; }
        key.Pressed(12, false);
        if (!key.Pressed(13, true)) { Console.WriteLine("FAIL second press cannot close history"); failures++; }
        return failures == 0 ? 0 : 1;
    }
}
