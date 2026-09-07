using System;
using System.IO;
using System.Collections.Generic;
using System.Security.Cryptography;

namespace Kibukawa.ImageReplacements
{
    public sealed class ReplacementEntry
    {
        public string Id, Canvas, Payload, Sha256;
        public int Index;
        public string Key { get { return Canvas+":"+Index; } }
    }
    public sealed class ReplacementManifest
    {
        public string Game, AssemblyHash, ScratchpadHash;
        public readonly List<ReplacementEntry> Entries=new List<ReplacementEntry>();
        public static string Hash(byte[] data)
        {
            using(var sha=SHA256.Create()) return BitConverter.ToString(sha.ComputeHash(data)).Replace("-","").ToLowerInvariant();
        }
        public static ReplacementManifest Read(string file)
        {
            string[] lines=File.ReadAllLines(file);
            if(lines.Length<2) throw new InvalidDataException("Empty image replacement manifest");
            string[] header=lines[0].Split('\t');
            if(header.Length!=4 || header[0]!="KIMG1") throw new InvalidDataException("Unsupported image replacement manifest");
            var result=new ReplacementManifest{Game=header[1],AssemblyHash=header[2],ScratchpadHash=header[3]};
            string root=Path.GetFullPath(Path.GetDirectoryName(file))+Path.DirectorySeparatorChar;
            var routes=new HashSet<string>();
            for(int line=1;line<lines.Length;line++)
            {
                if(string.IsNullOrWhiteSpace(lines[line]) || lines[line].StartsWith("#")) continue;
                string[] fields=lines[line].Split('\t');
                int index;
                if(fields.Length!=5 || !int.TryParse(fields[2],out index) || index<0 || index>4095)
                    throw new InvalidDataException("Invalid image entry on line "+(line+1));
                string payload=Path.GetFullPath(Path.Combine(root,fields[3]));
                if(Path.IsPathRooted(fields[3]) || !payload.StartsWith(root,StringComparison.OrdinalIgnoreCase))
                    throw new InvalidDataException("Image payload path leaves plugin directory");
                var entry=new ReplacementEntry{Id=fields[0],Canvas=fields[1],Index=index,Payload=payload,Sha256=fields[4]};
                if(!routes.Add(entry.Key)) throw new InvalidDataException("Duplicate image route: "+entry.Key);
                if(Hash(File.ReadAllBytes(payload))!=entry.Sha256) throw new InvalidDataException("Image payload checksum mismatch: "+entry.Id);
                result.Entries.Add(entry);
            }
            if(result.Entries.Count==0) throw new InvalidDataException("No image replacements configured");
            return result;
        }
    }
}
