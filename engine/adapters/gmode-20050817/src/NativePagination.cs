using System;
using System.Collections.Generic;
using System.Reflection;
using System.Runtime.CompilerServices;
using System.Security.Cryptography;
using HarmonyLib;

namespace Kibukawa.Engine.Gmode20050817
{
    internal static class NativePagination
    {
        sealed class State
        {
            internal object Script;
            internal readonly Kibukawa.Engine.GmodeV2.PageMemory Memory = new Kibukawa.Engine.GmodeV2.PageMemory();
        }
        static readonly ConditionalWeakTable<object,State> states = new ConditionalWeakTable<object,State>();
        static FieldInfo script, position, cursor, count, labels, indices, normal, longText, back;
        internal static void Initialize(Type canvas)
        {
            script=AccessTools.Field(canvas,"Script"); position=AccessTools.Field(canvas,"Pos");
            cursor=AccessTools.Field(canvas,"CommandCursorPos"); count=AccessTools.Field(canvas,"SentakuStock");
            labels=AccessTools.Field(canvas,"LabelIndex"); indices=AccessTools.Field(canvas,"Sentaku_index");
            normal=AccessTools.Field(canvas,"NowCommand"); longText=AccessTools.Field(canvas,"NowChobunCommand");
            back=AccessTools.Field(canvas,"komando_modori");
            if(script==null || position==null || cursor==null || count==null || labels==null || indices==null)
                throw new MissingFieldException("Pagination fields");
        }
        static State Get(object canvas)
        {
            var state=states.GetOrCreateValue(canvas);
            var raw=(sbyte[])script.GetValue(canvas);
            if(!Object.ReferenceEquals(raw,state.Script))
            {
                state.Script=raw;
                string hash=null; int[][] groups=null;
                if(raw!=null)
                {
                    byte[] bytes=new byte[raw.Length];Buffer.BlockCopy(raw,0,bytes,0,bytes.Length);
                    using(var sha=SHA256.Create()) hash=BitConverter.ToString(sha.ComputeHash(bytes)).Replace("-","").ToLowerInvariant();
                    NativePaginationData.Groups.TryGetValue(hash,out groups);
                }
                state.Memory.SelectScript(hash,groups);
            }
            return state;
        }
        internal static void Begin(object canvas)
        {
            position.SetValue(canvas,Get(canvas).Memory.Begin((int)position.GetValue(canvas)));
        }
        static bool Active(object canvas)
        {
            return (bool)normal.GetValue(canvas) || (bool)longText.GetValue(canvas);
        }
        internal static bool Restore(object canvas)
        {
            if(!Active(canvas)) return false;
            int value;
            if(!Get(canvas).Memory.Restore((int)count.GetValue(canvas),out value)) return false;
            cursor.SetValue(canvas,value); return true;
        }
        internal static bool Record(object canvas,bool cancel)
        {
            if(!Active(canvas)) return false;
            int value=(int)cursor.GetValue(canvas); int? target=null;
            if(!cancel)
            {
                var items=(int[])indices.GetValue(canvas);var targets=(int[])labels.GetValue(canvas);
                if(value>=0 && value<items.Length && items[value]>=0 && items[value]<targets.Length)
                    target=targets[items[value]]+1;
            }
            int returnTarget;
            if(!Get(canvas).Memory.Record(value,cancel,target,out returnTarget)) return false;
            if(cancel) back.SetValue(canvas,returnTarget);
            return true;
        }
    }
}
