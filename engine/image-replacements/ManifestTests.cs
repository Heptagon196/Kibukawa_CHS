using System;
using System.IO;
using Kibukawa.ImageReplacements;
public static class ManifestTests
{
    public static int Main(string[] args)
    {
        var manifest=ReplacementManifest.Read(args[0]);
        if(manifest.Entries.Count<1) throw new Exception("No image routes loaded");
        if(manifest.Game=="kibu2") foreach(var entry in manifest.Entries)
            if(entry.Canvas=="CanvasEx" && entry.Index==10) throw new Exception("Existing second-game map was overridden");
        string root=Path.Combine(Path.GetTempPath(),"kimg-manifest-"+Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(root);
        try {
            byte[] data=new byte[]{1,2,3,4};File.WriteAllBytes(Path.Combine(root,"test.rgba"),data);
            string hash=ReplacementManifest.Hash(data),header="KIMG1\tkibu4\tassembly\tscratch\n";
            string first="one\tappli1.CanvasEx\t16\ttest.rgba\t"+hash+"\n";
            string second="two\tappli1.CanvasEx\t17\ttest.rgba\t"+hash+"\n";
            string file=Path.Combine(root,"manifest.tsv");
            File.WriteAllText(file,header+first+second);
            if(ReplacementManifest.Read(file).Entries.Count!=2) throw new Exception("Multiple image routes failed");
            foreach(string invalid in new[]{header+first+first,header+"one\tCanvasEx\t1\t../bad.rgba\t"+hash,
                header+"one\tCanvasEx\t-1\ttest.rgba\t"+hash,header+first.Replace(hash,"bad")}) {
                File.WriteAllText(file,invalid);bool rejected=false;
                try{ReplacementManifest.Read(file);}catch(InvalidDataException){rejected=true;}
                if(!rejected) throw new Exception("Invalid manifest was accepted");
            }
            Console.WriteLine("PASS: "+manifest.Game+" routes, multiple images, duplicate routes, traversal, indices, checksums and map compatibility");
        } finally { File.Delete(Path.Combine(root,"test.rgba"));File.Delete(Path.Combine(root,"manifest.tsv"));Directory.Delete(root); }
        return 0;
    }
}
