using System;
using System.Collections.Generic;
using System.Security.Cryptography;
namespace Kibukawa.Engine.GmodeV2
{
    public sealed class MenuMemory
    {
        object script;
        string digest="";
        readonly Dictionary<string,int[]> entries=new Dictionary<string,int[]>();
        string Key(sbyte[] current,int menu)
        {
            if(!Object.ReferenceEquals(script,current))
            {
                script=current; digest="";
                if(current!=null)
                {
                    var bytes=new byte[current.Length]; Buffer.BlockCopy(current,0,bytes,0,bytes.Length);
                    using(var sha=SHA256.Create()) digest=Convert.ToBase64String(sha.ComputeHash(bytes));
                }
            }
            return digest+":"+menu;
        }
        public void Record(sbyte[] script,int menu,int cursor,int top)
        { entries[Key(script,menu)]=new[]{cursor,top}; }
        public bool Restore(sbyte[] script,int menu,int count,out int cursor,out int top)
        {
            int[] saved;cursor=0;top=0;
            if(!entries.TryGetValue(Key(script,menu),out saved)) return false;
            cursor=saved[0]>=0 && saved[0]<count ? saved[0] : 0;top=saved[1];return true;
        }
    }
}
