using System;
using System.Collections.Generic;

namespace Kibukawa.Engine.GmodeV2
{
    // One instance per live canvas. Script identity comes from the version adapter.
    public sealed class PageMemory
    {
        sealed class Group
        {
            internal int Back, Root, Last;
            internal readonly Dictionary<int,int> Cursors = new Dictionary<int,int>();
        }
        readonly Dictionary<string,Dictionary<int,Group>> scripts = new Dictionary<string,Dictionary<int,Group>>();
        Dictionary<int,Group> pages = new Dictionary<int,Group>();
        int current, explicitTarget;
        public void SelectScript(string identity, int[][] definitions)
        {
            current=0; explicitTarget=0;
            if(identity==null) { pages=new Dictionary<int,Group>(); return; }
            if(scripts.TryGetValue(identity,out pages)) return;
            pages=new Dictionary<int,Group>();
            if(definitions!=null) foreach(var row in definitions)
            {
                if(row.Length<2) throw new ArgumentException("Page group requires a back target and root");
                var group=new Group {Back=row[0],Root=row[1],Last=row[1]};
                for(int i=1;i<row.Length;i++) pages.Add(row[i],group);
            }
            scripts.Add(identity,pages);
        }
        public int Begin(int requested)
        {
            Group group;
            if(pages.TryGetValue(requested,out group))
            {
                if(requested==group.Root && explicitTarget!=requested) requested=group.Last;
                group.Last=requested;
            }
            current=requested; explicitTarget=0; return requested;
        }
        public bool Restore(int count,out int cursor)
        {
            cursor=0; Group group;
            if(!pages.TryGetValue(current,out group)) return false;
            group.Cursors.TryGetValue(current,out cursor);
            cursor=Math.Max(0,Math.Min(cursor,count-1)); return true;
        }
        public bool Record(int cursor,bool cancel,int? target,out int back)
        {
            back=0; Group group;
            if(!pages.TryGetValue(current,out group)) return false;
            group.Cursors[current]=cursor; group.Last=current; back=group.Back;
            Group next;
            if(!cancel && target.HasValue && pages.TryGetValue(target.Value,out next) && Object.ReferenceEquals(group,next))
                explicitTarget=target.Value;
            return true;
        }
    }
}
