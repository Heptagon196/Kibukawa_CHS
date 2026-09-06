using System;
using System.IO;
using Kibu1ZhCN;
using UnityEngine;

// Minimal managed stand-ins: this executable never loads or starts Unity.
namespace UnityEngine
{
    public class Object
    {
        public bool destroyed;
        public static void Destroy(Object value) { if(value!=null) value.destroyed=true; }
    }
    public enum FilterMode { Point }
    public enum TextureFormat { ARGB32, RGBA32 }
    public struct Color32
    {
        public byte r, g, b, a;
        public Color32(byte r, byte g, byte b, byte a) { this.r=r; this.g=g; this.b=b; this.a=a; }
    }
    public class Texture2D : Object
    {
        public int width, height;
        public bool unreadable;
        public int mipmapCount;
        public bool uploadedMipChain;
        public FilterMode filterMode;
        public Color32[] pixels;
        // The original Unity 2019.4 two-argument constructor requests GenerateAllMips.
        public Texture2D(int w, int h) : this(w,h,TextureFormat.RGBA32,true) { }
        public Texture2D(int w,int h,TextureFormat format,bool mipChain)
        { width=w; height=h; pixels=new Color32[w*h]; mipmapCount=mipChain ? 8 : 1; }
        public Color32[] GetPixels32() { if (unreadable) throw new Exception("Unreadable texture"); return (Color32[])pixels.Clone(); }
        public void SetPixels32(Color32[] value) { pixels=value; uploadedMipChain=false; }
        public void Apply(bool mipmaps, bool unreadable) { uploadedMipChain=mipmaps || mipmapCount==1; }
    }
}
public class FakeImage : UnityEngine.Object
{
    private Texture2D texture;
    public Texture2D factoryTexture;
    private bool isDisposable;
    public Texture2D Texture
    {
        get { return texture; }
        set
        {
            if(texture!=null) { IsDisposable=false; UnityEngine.Object.Destroy(texture); }
            texture=value;
        }
    }
    public bool IsDisposable { set { isDisposable=value; } }
    public bool disposed;
    public static int created;
    public FakeImage(int w,int h) { texture=new Texture2D(w,h); factoryTexture=texture; IsDisposable=true; }
    public static FakeImage CreateImage(int w,int h) { created++; return new FakeImage(w,h); }
    public void Dispose() { disposed=true; if(isDisposable) UnityEngine.Object.Destroy(texture); }
}
public class FloorPlanOverlayTests
{
    static int checks;
    static void Check(bool value) { checks++; if (!value) throw new Exception("Failed floor plan assertion " + checks); }
    public static void Main(string[] args)
    {
        var pixels=new[] { new Color32(1,2,3,255),new Color32(4,5,6,255),new Color32(7,8,9,255),new Color32(10,11,12,255) };
        var mask=new byte[] { 100,101,102,255, 0,0,0,0, 200,201,202,255, 100,100,100,128 };
        var combined=FloorPlanOverlay.Compose(pixels,mask,2,2);
        Check(combined[2].r==100 && combined[2].g==101 && combined[2].b==102);
        Check(combined[3].r==10 && combined[3].a==255);
        Check(combined[0].r==200 && combined[0].g==201);
        Check(combined[1].r==52 && combined[1].g==53 && combined[1].a==255);
        Check(pixels[0].r==1 && pixels[2].r==7);
        // Reproduce the legacy factory/upload mismatch before checking the fixed path.
        // A GPU may sample these unwritten mip levels as a uniform gray image.
        var legacy=new Texture2D(220,128);
        legacy.SetPixels32(new Color32[220*128]); legacy.Apply(false,false);
        Check(legacy.mipmapCount>1 && !legacy.uploadedMipChain);
        var decodedGif=new Texture2D(220,128,TextureFormat.ARGB32,false);
        decodedGif.SetPixels32(new Color32[220*128]); decodedGif.Apply(false,true);
        Check(decodedGif.mipmapCount==1 && decodedGif.uploadedMipChain);
        bool rejected=false;
        try { FloorPlanOverlay.Compose(pixels,new byte[1],2,2); } catch(ArgumentException) { rejected=true; }
        Check(rejected);
        string folder=Path.Combine(Path.GetTempPath(),"kibu2-map-test-"+Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(folder);
        string path=Path.Combine(folder,"floorplan.bin");
        try
        {
            using(var writer=new BinaryWriter(File.Create(path)))
            {
                writer.Write(0x50414D4B); writer.Write(220); writer.Write(128);
                var full=new byte[220*128*4]; full[0]=255;
                for(int i=3;i<full.Length;i+=4) full[i]=255;
                writer.Write(full);
            }
            int warnings=0;
            FloorPlanOverlay.Initialize(folder,delegate(string message) { warnings++; });
            var original=new FakeImage(220,128);
            Check(ReferenceEquals(original,FloorPlanOverlay.Replace(9,original)));
            Check(FakeImage.created==0);
            var small=new FakeImage(10,10);
            Check(ReferenceEquals(small,FloorPlanOverlay.Replace(10,small)));
            var translated=(FakeImage)FloorPlanOverlay.Replace(10,original);
            Check(!ReferenceEquals(translated,original) && FakeImage.created==1);
            if (!translated.Texture.uploadedMipChain)
            {
                Console.Error.WriteLine("FAIL: Gray map regression: replacement has uninitialized mip levels after upload");
                Environment.Exit(1);
            }
            Check(translated.Texture.uploadedMipChain);
            Check(translated.Texture.mipmapCount==1 && translated.factoryTexture.destroyed);
            Check(translated.Texture.pixels[127*220].r==255 && original.Texture.pixels[127*220].r==0);
            Check(ReferenceEquals(translated,FloorPlanOverlay.Replace(10,original)) && FakeImage.created==1);
            FloorPlanOverlay.Reset();
            Check(translated.disposed && !original.disposed);
            Check(translated.Texture.destroyed && !original.Texture.destroyed);
            FloorPlanOverlay.Initialize(folder,delegate(string message) { warnings++; });
            original.Texture.unreadable=true;
            translated=(FakeImage)FloorPlanOverlay.Replace(10,original);
            Check(!ReferenceEquals(original,translated) && warnings==0);
            Check(translated.Texture.pixels[127*220].r==255 && !original.disposed);
            Check(ReferenceEquals(translated,FloorPlanOverlay.Replace(10,original)));
            var transparent=File.ReadAllBytes(path); transparent[15]=0; File.WriteAllBytes(path,transparent);
            FloorPlanOverlay.Initialize(folder,delegate(string message) { warnings++; });
            Check(translated.disposed && warnings==1 && ReferenceEquals(original,FloorPlanOverlay.Replace(10,original)));
            File.WriteAllBytes(path,new byte[2]);
            FloorPlanOverlay.Initialize(folder,delegate(string message) { warnings++; });
            Check(warnings==2 && ReferenceEquals(original,FloorPlanOverlay.Replace(10,original)));
            Console.WriteLine("PASS: " + checks + " floor plan orientation, alpha, isolation, cache and failure assertions.");
        }
        finally { FloorPlanOverlay.Reset(); File.Delete(path); Directory.Delete(folder); }
    }
}
