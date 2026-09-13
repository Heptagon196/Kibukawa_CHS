using System;
using System.IO;
using System.Reflection;
using Kibukawa8.Runtime;
public static class MonoBindingProbe
{
    public static string Run()
    {
        try
        {
            string root=Environment.GetEnvironmentVariable("KIBU8_PROBE_WORK");
            var assembly=Assembly.LoadFrom(Environment.GetEnvironmentVariable("KIBU8_PROBE_ASSEMBLY"));
            var decoder=(Func<byte[],string>)Delegate.CreateDelegate(typeof(Func<byte[],string>),
                assembly.GetType("USEncoder.ToEncoding").GetMethod("ToUnicode",new[]{typeof(byte[])}));
            var pack=RuntimePack.Load(Path.Combine(root,"bepinex/build/plugin/translations.bin"),ScriptIdentityData.Names,decoder);
            int count=0;
            foreach(string file in Directory.GetFiles(Path.Combine(root,"raw"),"*.bin",SearchOption.AllDirectories))
            {
                byte[] raw=File.ReadAllBytes(file);int skip=17+2*(raw[15]+raw[16]*256);
                byte[] body=new byte[raw.Length-skip];Array.Copy(raw,skip,body,0,body.Length);
                var script=pack.Bind(body);if(script==null)throw new Exception("UNBOUND "+file);
                if(Path.GetFileName(file)=="c1-03.bin" && !script.Displays[72].Rows[0].Text.Contains("迷雾在线"))
                    throw new Exception("MO welcome not translated");
                count++;
            }
            if(count!=59)throw new Exception("Incomplete scenario coverage: "+count);
            return "PASS: actual game Mono + original decoder bind all 59 scripts, including MO welcome";
        }
        catch(Exception error) { return error.ToString(); }
    }
}
