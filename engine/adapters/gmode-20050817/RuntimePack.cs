using System;
using System.IO;
using System.Text;
using System.Security.Cryptography;
using System.Collections.Generic;

namespace Kibukawa8.Runtime
{
    public sealed class RuntimeRow
    {
        public string SourceText, Text, RubyJson;
        public byte[] Colors, Controls;
    }
    public sealed class DisplayTranslation
    {
        public int Offset;
        public byte Opcode;
        public RuntimeRow[] Rows;

        public void NormalizeAddedQuoteColors()
        {
            if(Rows.Length==0 || String.IsNullOrEmpty(Rows[0].Text) || Rows[0].Text[0]!='“' || Rows[0].Colors[0]==0) return;
            string source=Rows[0].SourceText ?? "";
            bool originalQuote=source.StartsWith("「") || source.StartsWith("『") || source.StartsWith("“") || source.StartsWith("‘");
            // A quoted source term becomes an inner single quote when the
            // translation adds a surrounding spoken-dialogue quotation.
            if(originalQuote && !Rows[0].Text.StartsWith("“‘")) return;
            Rows[0].Colors[0]=0;
            foreach(var row in Rows)
            {
                int close=row.Text.IndexOf('”');
                if(close>=0) { row.Colors[close]=0;break; }
            }
        }
    }
    public sealed class StringTranslation
    {
        public int Offset;
        public byte Opcode;
        public string Source, Target;
    }
    public sealed class ScriptTranslation
    {
        public readonly Dictionary<int, DisplayTranslation> Displays = new Dictionary<int, DisplayTranslation>();
        public readonly Dictionary<int, StringTranslation> Strings = new Dictionary<int, StringTranslation>();
    }
    // Shared KBZH schema: translations contain plain text. The immutable original
    // scenario supplies row boundaries, palette indices, and control events.
    public sealed class RuntimePack
    {
        public readonly Dictionary<string, ScriptTranslation> Scripts = new Dictionary<string, ScriptTranslation>(StringComparer.Ordinal);
        public Kibu1ZhCN.TranslationPack Data;
        private Dictionary<string,string> names;
        private readonly HashSet<string> bound = new HashSet<string>(StringComparer.Ordinal);
        private readonly Dictionary<string,Dictionary<int,List<Kibu1ZhCN.ScriptEntry>>> entries = new Dictionary<string,Dictionary<int,List<Kibu1ZhCN.ScriptEntry>>>(StringComparer.Ordinal);
        private static readonly Encoding Sjis = Encoding.GetEncoding(932, EncoderFallback.ExceptionFallback, DecoderFallback.ExceptionFallback);
        private Func<byte[],string> originalDecoder;
        private string Decode(byte[] data, int start, int length)
        {
            if (originalDecoder == null) return Sjis.GetString(data,start,length);
            var slice=new byte[length];Array.Copy(data,start,slice,0,length);
            return originalDecoder(slice);
        }
        public static RuntimePack Load(string path, Dictionary<string,string> scriptNames, Func<byte[],string> originalDecoder = null)
        {
            var pack = new RuntimePack { Data = Kibu1ZhCN.TranslationPackReader.Load(path), names = new Dictionary<string,string>(scriptNames,StringComparer.Ordinal), originalDecoder = originalDecoder };
            var known = new HashSet<string>(scriptNames.Values,StringComparer.Ordinal);
            foreach (var entry in pack.Data.scripts)
            {
                if (entry.script == null || !known.Contains(entry.script) || entry.instruction < 0 || entry.opcode < 0 || entry.opcode > 255 || entry.target == null || entry.source == null)
                    throw new InvalidDataException("Invalid VM translation entry");
                foreach(char c in entry.target)
                    if(c<32 || Char.IsSurrogate(c) || c=='<' || c=='>') throw new InvalidDataException("Translation must contain plain printable text");
                ScriptTranslation script;
                if (!pack.Scripts.TryGetValue(entry.script, out script))
                {
                    pack.Scripts.Add(entry.script, script = new ScriptTranslation());
                    pack.entries.Add(entry.script,new Dictionary<int,List<Kibu1ZhCN.ScriptEntry>>());
                }
                if (entry.slot == -1)
                {
                    if (entry.opcode!=5 && entry.opcode!=8 && entry.opcode!=17 && entry.opcode!=80) throw new InvalidDataException("Invalid string opcode");
                    script.Strings.Add(entry.instruction, new StringTranslation { Offset=entry.instruction, Opcode=(byte)entry.opcode, Source=entry.source, Target=entry.target });
                    continue;
                }
                if (entry.slot < 0 || (entry.opcode!=255 && entry.opcode!=72 && entry.opcode!=75 && entry.opcode!=120)) throw new InvalidDataException("Invalid display slot/opcode");
                List<Kibu1ZhCN.ScriptEntry> display;
                if(!pack.entries[entry.script].TryGetValue(entry.instruction,out display))
                    pack.entries[entry.script].Add(entry.instruction,display=new List<Kibu1ZhCN.ScriptEntry>());
                if(entry.slot!=display.Count || (display.Count!=0 && entry.opcode!=display[0].opcode)) throw new InvalidDataException("Unordered or duplicate display span");
                display.Add(entry);
            }
            return pack;
        }
        public ScriptTranslation Bind(byte[] original)
        {
            string hash;
            using(SHA256 sha=SHA256.Create()) hash=BitConverter.ToString(sha.ComputeHash(original)).Replace("-","").ToLowerInvariant();
            string name; ScriptTranslation script;
            if(!names.TryGetValue(hash,out name) || !Scripts.TryGetValue(name,out script)) return null;
            if(bound.Contains(name)) return script;
            // Stage all reconstructed displays before publishing a script binding.
            var displays=new Dictionary<int,DisplayTranslation>();
            foreach(var pair in entries[name])
            {
                int pos=pair.Key;
                byte op=Take(original,ref pos);
                if(op!=pair.Value[0].opcode) throw new InvalidDataException("Original display opcode mismatch");
                int count=1;
                if(op==255) { count=Take(original,ref pos);Take(original,ref pos); }
                var rows=new RuntimeRow[count]; int slot=0; byte lastColor=0;
                for(int i=0;i<count;i++) rows[i]=ReadRow(original,ref pos,op,pair.Value,ref slot,ref lastColor);
                if(slot!=pair.Value.Count) throw new InvalidDataException("Unexpected translated display spans");
                var display=new DisplayTranslation {Offset=pair.Key,Opcode=op,Rows=rows};
                display.NormalizeAddedQuoteColors();
                displays.Add(pair.Key,display);
            }
            foreach(var item in script.Strings.Values)
            {
                int end=item.Offset;
                while(end<original.Length && original[end]!=0) end++;
                if(end==original.Length || Decode(original,item.Offset,end-item.Offset)!=item.Source)
                    throw new InvalidDataException("Original string source mismatch");
            }
            foreach(var pair in displays) script.Displays.Add(pair.Key,pair.Value);
            bound.Add(name);
            return script;
        }
        private static byte Take(byte[] data,ref int pos)
        {
            if(pos<0 || pos>=data.Length) throw new InvalidDataException("Truncated original display");
            return data[pos++];
        }
        private static void Skip(byte[] data,ref int pos,int count)
        {
            if(count<0 || pos<0 || count>data.Length-pos) throw new InvalidDataException("Truncated original display plane");
            pos+=count;
        }
        private sealed class Span { public string Source; public byte Color,Control; }
        private RuntimeRow ReadRow(byte[] data,ref int pos,byte op,List<Kibu1ZhCN.ScriptEntry> entries,ref int slot,ref byte lastColor)
        {
            int n=Take(data,ref pos), textOffset=pos; Skip(data,ref pos,n*2);
            string source=Decode(data,textOffset,n*2);
            if(op==255 || op==75) Skip(data,ref pos,n);
            int colorsOffset=pos; Skip(data,ref pos,n);
            int controlsOffset=pos; bool hasControls=op==255 || op==120;
            if(hasControls) Skip(data,ref pos,n);
            if(op==255 || op==75)
            {
                int rubies=Take(data,ref pos);
                for(int i=0;i<rubies;i++) { Take(data,ref pos); int cells=Take(data,ref pos); Skip(data,ref pos,cells*2); }
            }
            var spans=new List<Span>(); var pending=new StringBuilder(); byte color=0;
            for(int i=0;i<n;i++)
            {
                byte next=data[colorsOffset+i];
                if(next!=color && pending.Length!=0) { spans.Add(new Span {Source=pending.ToString(),Color=color});pending.Length=0; }
                color=next;
                pending.Append(Decode(data,textOffset+i*2,2).Replace("\uf8f3",""));
                byte control=hasControls?data[controlsOffset+i]:(byte)0;
                if(control!=0)
                {
                    if(pending.Length!=0) {spans.Add(new Span {Source=pending.ToString(),Color=color});pending.Length=0;}
                    if(spans.Count==0 || spans[spans.Count-1].Control!=0) spans.Add(new Span {Source="",Color=color});
                    spans[spans.Count-1].Control=control;
                }
            }
            if(pending.Length!=0) spans.Add(new Span {Source=pending.ToString(),Color=color});
            var text=new StringBuilder();var colors=new List<byte>();var controls=new List<byte>();
            foreach(var span in spans)
            {
                if(slot>=entries.Count || entries[slot].source!=span.Source) throw new InvalidDataException("Original display span mismatch at slot "+slot+" expected UTF16="+(slot<entries.Count?BitConverter.ToString(Encoding.Unicode.GetBytes(entries[slot].source)):"missing")+" actual UTF16="+BitConverter.ToString(Encoding.Unicode.GetBytes(span.Source)));
                string target=entries[slot++].target;
                if(span.Source.Length!=0) lastColor=span.Color;
                text.Append(target);
                for(int i=0;i<target.Length;i++) {colors.Add(lastColor);controls.Add(0);}
                if(span.Control!=0)
                {
                    if(controls.Count==0 || controls[controls.Count-1]!=0) {text.Append('\u3000');colors.Add(lastColor);controls.Add(0);}
                    controls[controls.Count-1]=span.Control;
                }
            }
            return new RuntimeRow {SourceText=source,Text=text.ToString(),Colors=colors.ToArray(),Controls=controls.ToArray(),RubyJson="{}"};
        }
    }
}
