using System;
using System.IO;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Drawing.Text;
using System.Web.Script.Serialization;

// Code-native UI labels are composed offline; runtime loads the finished map.
public static class RenderFloorPlanLabels
{
    public sealed class Label { public string source, text, background, color; public int x,y,width,height,size,tx; }
    public sealed class Layout { public int width,height; public string font; public Label[] labels; }
    static Color Parse(string s) { return Color.FromArgb(255, Convert.ToInt32(s.Substring(0,2),16),Convert.ToInt32(s.Substring(2,2),16),Convert.ToInt32(s.Substring(4,2),16)); }
    public static void Main(string[] args)
    {
        try { Render(args); }
        catch(Exception e) { File.WriteAllText(args[3]+"-error.txt",e.GetType().Name+"\n"+e.Message+"\n"+e.StackTrace); Environment.ExitCode=1; }
    }
    static void Render(string[] args)
    {
        var layout=new JavaScriptSerializer().Deserialize<Layout>(File.ReadAllText(args[0]));
        if(layout.width!=220 || layout.height!=128) throw new Exception("Unexpected map dimensions");
        using(var overlay=new Bitmap(layout.width,layout.height))
        using(var original=new Bitmap(args[1]))
        using(var g=Graphics.FromImage(overlay))
        {
            g.TextRenderingHint=TextRenderingHint.SingleBitPerPixelGridFit;
            foreach(var label in layout.labels)
            {
                float advance=0; foreach(char c in label.text) advance+=c<128?label.size/2f:label.size;
                if(label.x<0 || label.y<0 || label.x+label.width>220 || label.y+label.height>128 || advance>label.width) throw new Exception("Label exceeds rectangle: "+label.text);
                using(var bg=new SolidBrush(Parse(label.background))) g.FillRectangle(bg,label.x,label.y,label.width,label.height);
                using(var font=new Font(layout.font,label.size,FontStyle.Regular,GraphicsUnit.Pixel))
                using(var brush=new SolidBrush(Parse(label.color)))
                using(var format=(StringFormat)StringFormat.GenericTypographic.Clone())
                {
                    if(font.Name!=layout.font && font.Name!="宋体") throw new Exception("Required font unavailable: "+layout.font);
                    format.FormatFlags=StringFormatFlags.NoWrap|StringFormatFlags.NoClip;
                    g.SetClip(new Rectangle(label.x,label.y,label.width,label.height));
                    g.DrawString(label.text,font,brush,label.tx==0?label.x:label.tx,label.y,format);
                    g.ResetClip();
                }
            }
            overlay.Save(args[2]+".png");
            using(var preview=new Bitmap(original))
            {
                using(var p=Graphics.FromImage(preview)) p.DrawImageUnscaled(overlay,0,0);
                using(var writer=new BinaryWriter(File.Create(args[2]+".bin")))
                {
                    writer.Write(new byte[]{75,77,65,80}); writer.Write(220); writer.Write(128);
                    for(int y=0;y<128;y++) for(int x=0;x<220;x++)
                    { var c=preview.GetPixel(x,y); writer.Write(c.R);writer.Write(c.G);writer.Write(c.B);writer.Write((byte)255); }
                }
                preview.Save(args[3]+".png");
                using(var large=new Bitmap(1320,768))
                using(var p=Graphics.FromImage(large))
                {
                    p.InterpolationMode=InterpolationMode.NearestNeighbor; p.PixelOffsetMode=PixelOffsetMode.Half;
                    p.DrawImage(preview,new Rectangle(0,0,1320,768),0,0,220,128,GraphicsUnit.Pixel);
                    large.Save(args[3]+"-6x.png");
                }
            }
        }
        Console.WriteLine("Rendered "+layout.labels.Length+" Chinese floor-plan UI labels.");
    }
}
