using System;
using System.IO;
using System.Text;

namespace Kibu1ZhCN
{
    // Unity's native JsonUtility does not reliably deserialize arrays of types
    // from a plugin assembly loaded after player startup. This reader is shared
    // verbatim by the live plugin and the full-corpus regression test.
    public static class TranslationPackReader
    {
        private static readonly UTF8Encoding Utf8 = new UTF8Encoding(false, true);
        private static int Count(BinaryReader reader)
        {
            int count = reader.ReadInt32();
            if (count < 0 || count > 100000) throw new InvalidDataException("Invalid translation count");
            return count;
        }
        private static string Text(BinaryReader reader)
        {
            int size = reader.ReadInt32();
            if (size == -1) return null;
            if (size < 0 || size > 20000000) throw new InvalidDataException("Invalid translation string size");
            byte[] data = reader.ReadBytes(size);
            if (data.Length != size) throw new EndOfStreamException("Truncated translation string");
            return Utf8.GetString(data);
        }
        private static StringEntry[] Strings(BinaryReader reader)
        {
            var result = new StringEntry[Count(reader)];
            for (int i = 0; i < result.Length; i++)
                result[i] = new StringEntry { source = Text(reader), target = Text(reader), key = Text(reader) };
            return result;
        }
        public static TranslationPack Load(string path)
        {
            using (var reader = new BinaryReader(File.OpenRead(path)))
            {
                if (reader.ReadUInt32() != 0x485A424B) throw new InvalidDataException("Invalid translation file signature");
                var pack = new TranslationPack { schema = reader.ReadInt32(), gameAssemblySha256 = Text(reader), scratchpadSha256 = Text(reader) };
                if (pack.schema != 1) throw new InvalidDataException("Unsupported translation file version");
                pack.scripts = new ScriptEntry[Count(reader)];
                for (int i = 0; i < pack.scripts.Length; i++)
                    pack.scripts[i] = new ScriptEntry { index = reader.ReadInt32(), instruction = reader.ReadInt32(), slot = reader.ReadInt32(), opcode = reader.ReadInt32(), script = Text(reader), source = Text(reader), target = Text(reader) };
                pack.ui = Strings(reader);
                pack.localization = Strings(reader);
                pack.literals = new LiteralEntry[Count(reader)];
                for (int i = 0; i < pack.literals.Length; i++)
                    pack.literals[i] = new LiteralEntry { index = reader.ReadInt32(), token = reader.ReadInt32(), instruction = reader.ReadInt32(), source = Text(reader), target = Text(reader), method = Text(reader) };
                if (pack.scripts.Length == 0 || pack.ui.Length == 0 || reader.BaseStream.Position != reader.BaseStream.Length)
                    throw new InvalidDataException("Incomplete translation pack or unexpected trailing data");
                return pack;
            }
        }
    }
}
