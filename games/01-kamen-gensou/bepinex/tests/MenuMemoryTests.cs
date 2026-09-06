using System;
using Kibu1ZhCN;

// This fixture models the three game call sites, not the memory implementation:
// Read exposes a menu, Script initializes its cursor, and Jump leaves the menu.
public sealed class MenuCanvas
{
    internal int Cmd;
    internal sbyte Scene = 2, Scenario = 1, ScSelect = 0;
    internal bool Truth = true;
    internal string[] ScStr = new string[20];
    internal int[] ScInt = new int[20];
    internal sbyte[] Select = new sbyte[2];
}

public static class MenuMemoryTests
{
    private static int assertions;

    private static void Equal(int expected, int actual, string description)
    {
        assertions++;
        if (actual != expected)
            throw new Exception(description + ": expected " + expected + ", got " + actual);
    }

    private static MenuCanvas Fresh()
    {
        MenuSelectionMemory.Reset();
        MenuSelectionMemory.Initialize(typeof(MenuCanvas));
        return new MenuCanvas();
    }

    private static void Enter(MenuCanvas canvas, int instruction, int menuBase,
        string[] labels, int[] destinations)
    {
        canvas.Cmd = menuBase + labels.Length - 1;
        Array.Clear(canvas.ScStr, 0, canvas.ScStr.Length);
        Array.Clear(canvas.ScInt, 0, canvas.ScInt.Length);
        Array.Copy(labels, canvas.ScStr, labels.Length);
        Array.Copy(destinations, canvas.ScInt, destinations.Length);
        canvas.ScInt[labels.Length] = 999; // Original cancel branch, not a choice.
        MenuSelectionMemory.RecordMenu(canvas, instruction);
        canvas.Select[0] = 3; // Text row; restoring a choice must not change it.
        canvas.Select[1] = (sbyte)MenuSelectionMemory.Restore(canvas);
        Equal(3, canvas.Select[0], "preserve menu text row");
    }

    private static void Leave(MenuCanvas canvas, int index)
    {
        canvas.Select[1] = (sbyte)index;
        MenuSelectionMemory.Remember(canvas);
    }

    private static void RememberConfirmedChoice()
    {
        MenuCanvas canvas = Fresh();
        string[] labels = { "调查", "交谈", "移动" };
        int[] branches = { 1000, 2000, 3000 };
        Enter(canvas, 100, 105, labels, branches);
        Equal(0, canvas.Select[1], "first visit starts at first choice");
        Leave(canvas, 1);
        Enter(canvas, 100, 105, labels, branches);
        Equal(1, canvas.Select[1], "confirmed second choice restored");
        Leave(canvas, 2);
        Enter(canvas, 100, 105, labels, branches);
        Equal(2, canvas.Select[1], "latest choice supersedes previous choice");
    }

    private static void KeepMenusIndependent()
    {
        MenuCanvas canvas = Fresh();
        string[] labels = { "调查", "交谈", "移动" };
        int[] branches = { 1000, 2000, 3000 };
        Enter(canvas, 100, 105, labels, branches);
        Leave(canvas, 1);
        Enter(canvas, 200, 105, new[]{"桌子","电视","外套"}, new[]{4000,5000,6000});
        Equal(0, canvas.Select[1], "different menu actions have independent cursor");
        Leave(canvas, 2);
        Enter(canvas, 100, 105, labels, branches);
        Equal(1, canvas.Select[1], "returning parent menu remembers its own cursor");
        canvas.Scenario = 2;
        Enter(canvas, 100, 105, labels, branches);
        Equal(0, canvas.Select[1], "same instruction in another scenario is independent");
        Leave(canvas, 2);
        canvas.Scenario = 1;
        Enter(canvas, 100, 105, labels, branches);
        Equal(1, canvas.Select[1], "original scenario retains cursor");
        canvas.ScSelect = 1;
        Enter(canvas, 100, 105, labels, branches);
        Equal(0, canvas.Select[1], "another script bank is independent");
    }

    private static void FollowChoiceIdentity()
    {
        MenuCanvas canvas = Fresh();
        Enter(canvas, 100, 105, new[] { "调查", "交谈", "移动" }, new[] { 1000, 2000, 3000 });
        Leave(canvas, 2);
        Enter(canvas, 100, 105, new[] { "移动", "调查", "交谈" }, new[] { 3000, 1000, 2000 });
        Equal(0, canvas.Select[1], "reordered choice follows text and branch");

        canvas = Fresh();
        Enter(canvas, 100, 105, new[] { "调查", "交谈", "移动" }, new[] { 1000, 2000, 3000 });
        Leave(canvas, 2);
        Enter(canvas, 100, 105, new[] { "交谈", "移动" }, new[] { 2000, 3000 });
        Equal(1, canvas.Select[1], "removing another choice follows surviving choice");

        canvas = Fresh();
        Enter(canvas, 100, 105, new[] { "调查", "交谈", "移动" }, new[] { 1000, 2000, 3000 });
        Leave(canvas, 1);
        Enter(canvas, 100, 105, new[] { "调查", "移动" }, new[] { 1000, 3000 });
        Equal(0, canvas.Select[1], "deleted choice falls back to first");

        canvas = Fresh();
        Enter(canvas, 100, 105, new[] { "调查", "交谈" }, new[] { 1000, 2000 });
        Leave(canvas, 1);
        Enter(canvas, 100, 105, new[] { "调查", "交谈" }, new[] { 1000, 4000 });
        Equal(0, canvas.Select[1], "same label with changed branch is not same choice");

        canvas = Fresh();
        Enter(canvas, 100, 105, new[] { "调查", "交谈" }, new[] { 1000, 2000 });
        Leave(canvas, 1);
        Enter(canvas, 100, 105, new[] { "调查", "询问" }, new[] { 1000, 2000 });
        Equal(0, canvas.Select[1], "same branch with changed label is not same choice");
    }

    private static void CancelAndSingleColumn()
    {
        MenuCanvas canvas = Fresh();
        string[] labels = { "询问案件", "询问证物", "询问人物" };
        int[] branches = { 1000, 2000, 3000 };
        Enter(canvas, 300, 120, labels, branches);
        canvas.Select[1] = 2;
        // The cancel Jump calls Remember before taking the cancel destination.
        // Its destination must not replace the currently highlighted choice.
        MenuSelectionMemory.Remember(canvas);
        Enter(canvas, 300, 120, labels, branches);
        Equal(2, canvas.Select[1], "cancel remembers highlighted single-column choice");
    }

    private static void DoNotLeakBetweenGameInstances()
    {
        MenuCanvas first = Fresh();
        string[] labels = { "调查", "交谈" };
        int[] branches = { 1000, 2000 };
        Enter(first, 100, 105, labels, branches);
        Leave(first, 1);
        MenuCanvas second = new MenuCanvas();
        Enter(second, 100, 105, labels, branches);
        Equal(0, second.Select[1], "new canvas does not inherit old game's choices");
        Enter(first, 100, 105, labels, branches);
        Equal(1, first.Select[1], "first canvas retains its own choices");
        MenuSelectionMemory.Reset();
        MenuSelectionMemory.Initialize(typeof(MenuCanvas));
        Enter(first, 100, 105, labels, branches);
        Equal(0, first.Select[1], "reset removes session choices");
    }

    public static int Main()
    {
        try
        {
            GrowingInvestigationMenu();
            RememberConfirmedChoice();
            KeepMenusIndependent();
            FollowChoiceIdentity();
            CancelAndSingleColumn();
            DoNotLeakBetweenGameInstances();
            Console.WriteLine("Menu memory: " + assertions + " assertions passed.");
            return 0;
        }
        catch (Exception error)
        {
            Console.Error.WriteLine(error);
            return 1;
        }
    }
    private static void GrowingInvestigationMenu()
    {
        MenuCanvas canvas=Fresh();
        // Actual scn1 variants: learning about the phone selects a new opcode/address.
        Enter(canvas,4733,105,new[]{"桌子","电视","游戏机","窗户","书桌","外套"},new[]{4921,5473,5876,6537,6747,8240});
        Leave(canvas,5);
        Enter(canvas,4786,105,new[]{"桌子","电视","游戏机","窗户","书桌","外套","手机"},new[]{4921,5473,5876,6537,6747,8240,8933});
        Equal(5,canvas.Select[1],"adding phone at a different script instruction retains coat");
        Leave(canvas,6);
        Enter(canvas,4850,105,new[]{"桌子","电视","游戏机","窗户","书桌","外套","手机","钥匙"},new[]{4921,5473,5876,6537,6747,8240,8933,9722});
        Equal(6,canvas.Select[1],"adding key retains phone");
        Leave(canvas,7);
        Enter(canvas,4786,105,new[]{"桌子","电视","游戏机","窗户","书桌","外套","手机"},new[]{4921,5473,5876,6537,6747,8240,8933});
        Equal(0,canvas.Select[1],"removing remembered key falls back instead of using a stale variant cursor");
        canvas=Fresh();
        Enter(canvas,2519,105,new[]{"伊纲","门","电视"},new[]{2642,2584,2695});
        Leave(canvas,2);
        Enter(canvas,2551,105,new[]{"伊纲","门","电视","红茶"},new[]{2642,2584,3383,3347});
        Equal(2,canvas.Select[1],"unlocked TV branch retains the same named item");
        Leave(canvas,3);
        Enter(canvas,9999,105,new[]{"伊纲","门","电视","红茶"},new[]{2642,2584,3383,3347});
        Equal(3,canvas.Select[1],"equivalent conditional variant shares latest selection");
        canvas.Cmd=108;
        canvas.ScInt[4]=888;
        MenuSelectionMemory.RecordMenu(canvas,10001);
        Equal(0,MenuSelectionMemory.Restore(canvas),"different return destination isolates otherwise matching options");
        Enter(canvas,2551,105,new[]{"伊纲","门","电视","红茶"},new[]{2642,2584,3383,3347});
        Equal(3,canvas.Select[1],"returning to a known variant retains family selection");
        Leave(canvas,2);
        Enter(canvas,2552,105,new[]{"红茶","伊纲","门","电视","书架"},new[]{3347,2642,2584,3383,9000});
        Equal(3,canvas.Select[1],"new option and reordered variant follow item instead of index");
    }
}
