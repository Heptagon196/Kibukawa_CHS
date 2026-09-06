using System;
using System.IO;
using System.Linq;
using System.Web.Script.Serialization;
using Kibu1ZhCN;

public static class SentencePuzzleTests
{
    public sealed class Command { public string script; public int instruction,opcode; public string[] expected,strings; public int[] integers; }
    public sealed class Replay { public Command[] commands; }
    sealed class Menu
    {
        public int opcode; public string[] labels=new string[16]; public int[] targets=new int[16];
        public int Count { get { return opcode-105+1; } }
        public int Cancel { get { return targets[Count]; } }
    }
    static int checks;
    static void Check(bool ok,string reason) { checks++; if(!ok) throw new Exception(reason); }
    static Menu Load(Command[] commands,int address,bool translated)
    {
        var c=commands.Single(x=>x.script=="scn7" && x.instruction==address);
        var m=new Menu{opcode=c.opcode}; c.expected.CopyTo(m.labels,0);c.integers.CopyTo(m.targets,0);
        if(translated) m.opcode=SentencePuzzleLayout.Apply("scn7",address,m.opcode,m.labels,m.targets);
        return m;
    }
    public static int Main(string[] args)
    {
        try
        {
            var commands=new JavaScriptSerializer{MaxJsonLength=100000000}.Deserialize<Replay>(File.ReadAllText(args[0])).commands;
            var root=Load(commands,13967,true);
            Check(root.Count==2 && root.Cancel==65535,"Subject menu changed");
            for(int subject=0;subject<2;subject++)
            {
                int secondAddress=root.targets[subject];
                var originalObjects=Load(commands,secondAddress,false);
                var verbs=Load(commands,secondAddress,true);
                Check(verbs.Count==2 && verbs.labels.Take(2).SequenceEqual(new[]{"能变成","不能变成"}),"Verb must precede object");
                Check(verbs.Cancel==13967,"Verb cancel must return to subject");
                for(int verb=0;verb<2;verb++)
                {
                    var objects=Load(commands,verbs.targets[verb],true);
                    Check(objects.Count==3 && objects.labels.Take(3).SequenceEqual(originalObjects.labels.Take(3)),"Object menu changed choices");
                    Check(objects.Cancel==secondAddress,"Object cancel lost subject/verb stage");
                    for(int obj=0;obj<3;obj++)
                    {
                        int originalDestination=Load(commands,originalObjects.targets[obj],false).targets[verb];
                        Check(objects.targets[obj]==originalDestination,"Answer branch changed");
                        Check(commands.Any(x=>x.script=="scn7" && x.instruction==objects.targets[obj]),"Answer target is not an original instruction");
                        string sentence=root.labels[subject]+verbs.labels[verb]+objects.labels[obj];
                        if(subject==1 && verb==0 && obj==0)
                            Check(sentence=="连接通道能变成电梯" && objects.targets[obj]==14906,"Correct answer grammar or branch changed");
                    }
                    foreach(string label in objects.labels.Take(objects.Count)) Check(label.Length<=4,"Object exceeds menu width");
                }
            }
            foreach(int address in new[]{13992,14027,14048,14090,14125,14146})
            {
                var m=Load(commands,address,false); var before=m.labels.ToArray();var targets=m.targets.ToArray();
                Check(SentencePuzzleLayout.Apply("scn6",address,m.opcode,m.labels,m.targets)==m.opcode && m.labels.SequenceEqual(before) && m.targets.SequenceEqual(targets),"Other scene changed");
                // A malformed source node must not be partially rewritten.
                m.targets[0]=-42; targets=m.targets.ToArray();
                int result=SentencePuzzleLayout.Apply("scn7",address,m.opcode,m.labels,m.targets);
                Check(result==m.opcode && m.labels.SequenceEqual(before) && m.targets.SequenceEqual(targets),"Mismatched node was rewritten");
            }
            Console.WriteLine("PASS: "+checks+" sentence-puzzle checks; all 12 answer outcomes preserved; Chinese subject-verb-object order and cancel paths.");
            return 0;
        }
        catch(Exception e) { Console.WriteLine("FAIL: "+e.Message); return 1; }
    }
}
