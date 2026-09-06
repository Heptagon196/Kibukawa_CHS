using System;
using System.Collections.Generic;
using System.IO;
using System.Web.Script.Serialization;
using Kibu1ZhCN;

public sealed class Command {
    public string script;
    public int instruction, opcode, nextCursor;
    public string[] expected;
}
public sealed class Commands { public Command[] commands; }
public static class PunctuationLayoutTests {
    static List<string> Render(Command[] commands, bool corrected) {
        var rows = new List<string>();
        string script=null, row="";
        foreach (var c in commands) {
            bool boundary=c.script!=script || c.opcode==71 || c.opcode==73 || c.opcode==75 || c.opcode==76 || c.opcode==77 || c.opcode==78 || (c.opcode>=105 && c.opcode<=112) || (c.opcode>=120 && c.opcode<=123);
            if (corrected && c.opcode==77 && PunctuationLayout.ShouldSuppressNewline(c.script,c.nextCursor)) boundary=false;
            if (boundary) { if(row!="") rows.Add(row); row=""; }
            script=c.script;
            if (c.opcode==72 && c.expected.Length>0) row+=c.expected[0]??"";
        }
        if(row!="") rows.Add(row);
        return rows;
    }
    static void Check(bool value,string message) { if(!value) throw new Exception(message); }
    static bool PunctuationOnly(string text) {
        if(text.Trim().Length==0) return false;
        foreach(char c in text.Trim()) if(!char.IsPunctuation(c)) return false;
        return true;
    }
    public static void Main(string[] args) {
        var json=new JavaScriptSerializer { MaxJsonLength=50000000 };
        var commands=json.Deserialize<Commands>(File.ReadAllText(args[0])).commands;
        var before=Render(commands,false); var after=Render(commands,true);
        Check(before.FindAll(s=>s=="。").Count==3,"Original standalone full stops no longer reproduce");
        Check(after.FindAll(s=>s=="。").Count==0,"Standalone full stop remains");
        Check(string.Concat(before)==string.Concat(after),"Text changed during line joining");
        Check(string.Join("|",before.FindAll(s=>s.EndsWith("，")))==string.Join("|",after.FindAll(s=>s.EndsWith("，"))),"Comma-ending rows changed");
        Check(before.FindAll(PunctuationOnly).Count==77 && after.FindAll(PunctuationOnly).Count==73,"Punctuation audit coverage changed");
        Check(after.Contains("的制作人，濑堂！”"),"Exclamation and closing quote remain stranded");
        Check(!PunctuationLayout.ShouldSuppressNewline("scn6",1170),"Player-list continuation was changed");
        Check(!PunctuationLayout.ShouldSuppressNewline("scn8",1579),"Deliberate silence was changed");
        Check(after.Contains("侦探事务所。"),"Screenshot case not fixed");
        Check(after.Contains("她叫白鹭洲伊纲。") && after.Contains("癸生川凌介。"),"Name-reading cases not fixed");
        Check(!PunctuationLayout.ShouldSuppressNewline("scn1",371),"Join leaked into another scenario");
        Check(!PunctuationLayout.ShouldSuppressNewline("scn0",350),"Unrelated newline suppressed");
        Console.WriteLine("PASS: 77 punctuation-only rows audited; 4 stranded endings joined; text, comma-ending rows and deliberate pauses preserved.");
    }
}
