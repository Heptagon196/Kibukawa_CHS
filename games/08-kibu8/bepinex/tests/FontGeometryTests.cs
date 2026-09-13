using System;
using System.Collections.Generic;
using Kibu1ZhCN;
using UnityEngine;

// These recording doubles exercise the actual renderer source, without Unity or a game window.
namespace UnityEngine {
 public class Object { public static void Destroy(Object value) {} }
 public struct Vector2 { public float x,y; public Vector2(float a,float b){x=a;y=b;} }
 public struct Vector3 { public float x,y,z; public Vector3(float a,float b,float c){x=a;y=b;z=c;} }
 public struct Color {}
 public struct Quaternion { public static Quaternion identity { get {return new Quaternion();} } }
 public struct Matrix4x4 { public Vector3 position,scale; public static Matrix4x4 TRS(Vector3 p,Quaternion q,Vector3 s){return new Matrix4x4{position=p,scale=s};} }
 public struct CharacterInfo { public int advance,minX,maxX,minY,maxY; public Vector2 uvBottomLeft,uvBottomRight,uvTopRight,uvTopLeft; }
 public static class Mathf { public static float Round(float v){return (float)Math.Round(v);} public static float Min(float a,float b){return Math.Min(a,b);} }
 public class Mesh:Object { public Vector3[] vertices; public Vector2[] uv; public int[] triangles; }
 public class RenderTexture { public static RenderTexture active; public int width=240,height=240; }
 public class Material { public string name; public void SetColor(string key,Color value){} public bool SetPass(int pass){Graphics.material=this;return true;} }
 public class Font {
  public int lineHeight=37,ascent=28; // Deliberately differ from the requested size.
  public Material material=new Material{name="original"};
  public void RequestCharactersInTexture(string text,int size){}
  public bool GetCharacterInfo(char c,out CharacterInfo info,int size){
   info=new CharacterInfo{advance=size,minX=1,maxX=11,minY=-2,maxY=10};
   return "国田口日Q".IndexOf(c)>=0;
  }
 }
 public static class GL { public static int depth; public static void PushMatrix(){depth++;} public static void PopMatrix(){depth--;} public static void LoadPixelMatrix(float a,float b,float c,float d){} }
 public static class Graphics {
  public sealed class Call { public Mesh mesh; public Matrix4x4 matrix; public Material material; }
  public static Material material; public static readonly List<Call> calls=new List<Call>();
  public static void DrawMeshNow(Mesh mesh,Matrix4x4 matrix){calls.Add(new Call{mesh=mesh,matrix=matrix,material=material});}
 }
}
namespace Kibu1ZhCN {
 public sealed class BitmapFontAtlas {
  public int PixelSize; public Material material; public int lookups;
  public bool HasNativeBearings {get{return PixelSize==12;}}
  public BitmapFontAtlas(int size){PixelSize=size;material=new Material{name="bitmap"+size};}
  public bool TryGetForDisplay(char c,out CharacterInfo info){
   c=Kibukawa.Engine.Gmode20050817.LatinMetrics.Display(c);
   lookups++; float tag=PixelSize/100f;
   info=new CharacterInfo{advance=c<128?PixelSize/2:PixelSize,minX=0,maxX=c<128?PixelSize/2:PixelSize,minY=-3,maxY=11,
    uvBottomLeft=new Vector2(tag,0),uvBottomRight=new Vector2(tag+0.01f,0),uvTopRight=new Vector2(tag+0.01f,1),uvTopLeft=new Vector2(tag,1)};
   return c!='Q';
  }
  public Material MaterialFor(Font font){return material;}
 }
}
public static class FontGeometryTests {
 public class Wrapper { public Font font=new Font(); public float Size{get;set;} }
 public class Surface {
  public Wrapper currentFont=new Wrapper{Size=12}; public RenderTexture renderTexture=new RenderTexture(); public Color currentColor;
  public int begin,end; private void RenderStart(){begin++;RenderTexture.active=renderTexture;} private void RenderEnd(){end++;}
 }
 static void Equal(float actual,float expected,string label){if(Math.Abs(actual-expected)>0.00001)throw new Exception(label+": expected "+expected+", got "+actual);}
 static void Check(bool value,string label){if(!value)throw new Exception(label);}
 static Graphics.Call Draw(Surface surface,string value,BitmapFontAtlas large,BitmapFontAtlas small){
  Graphics.calls.Clear();var previous=new RenderTexture();RenderTexture.active=previous;
  Check(!LegacyFontRenderer.Draw(surface,value.ToCharArray(),31,70,null,large,1f,small),"replacement must consume draw");
  Check(object.ReferenceEquals(previous,RenderTexture.active),"restore render target"); Check(GL.depth==0&&surface.begin==surface.end,"balanced render scopes");
  var result=Graphics.calls[Graphics.calls.Count-1]; Equal(result.matrix.position.x,31,"draw x");Equal(result.matrix.position.y,170,"native height-y baseline");Equal(result.matrix.scale.x,1,"no horizontal resampling");Equal(result.matrix.scale.y,1,"no vertical resampling");return result;
 }
 static void Rect(Graphics.Call call,int index,float left,float width,float height,float top=10){var v=call.mesh.vertices;int n=index*4;Equal(v[n].x,left,"glyph x");Equal(v[n+1].x-v[n].x,width,"glyph width");Equal(v[n+2].y-v[n+1].y,height,"glyph height");Equal(v[n+2].y,top,"glyph top");}
 public static string Run(){
  var s=new Surface();var big=new BitmapFontAtlas(16);var small=new BitmapFontAtlas(12);
  var call=Draw(s,"中A文",big,small);Check(call.material==small.material,"12px surface must select small atlas");Check(big.lookups==0,"16px atlas must not supply small glyphs");
  Rect(call,0,0,12,14,11);Rect(call,1,12,6,14,11);Rect(call,2,18,12,14,11);Equal(call.mesh.vertices[0].y,-3,"BDF descender retained");Equal(call.mesh.uv[0].x,0.12f,"small atlas UV preserved");
  // If a caller supplies only a 16px bitmap, never silently downsample it to 12px.
  call=Draw(s,"中",big,null);Rect(call,0,0,16,16);Equal(call.mesh.uv[0].x,0.16f,"large atlas UV preserved");
  call=Draw(s,"中文",big,null);
  Check(call.mesh.vertices[4].x>=call.mesh.vertices[1].x,"Unifont string glyphs must not overlap in a nominal 12px context");
  call=Draw(s,"A中A文",big,null);
  Rect(call,0,0,8,16);Rect(call,1,8,16,16);Rect(call,2,24,8,16);Rect(call,3,32,16,16);
  // Native fullwidth VM slots select the same halfwidth atlas glyphs as ASCII.
  // Their mesh origin and advance must also match, not center inside a CJK cell.
  call=Draw(s,"Ｍ２",big,null);
  Rect(call,0,0,8,16);Rect(call,1,8,8,16);
  Graphics.calls.Clear();
  LegacyFontRenderer.Draw(s,"中".ToCharArray(),2,8,null,big,1f,null,1f);
  var header=Graphics.calls[0];
  float headerTop=240-(header.matrix.position.y+header.mesh.vertices[2].y);
  float headerBottom=240-(header.matrix.position.y+header.mesh.vertices[0].y);
  Equal(headerTop,1,"INFO absolute top ignores the original font ascent");
  Equal(headerBottom,17,"INFO preserves all 16 native ink rows");
  s.currentFont.Size=16;call=Draw(s,"中A",big,small);Check(call.material==big.material,"16px surface selects large atlas");Rect(call,0,0,16,16);Rect(call,1,16,8,16);
  call=Draw(s,"Ｍ２",big,small);Rect(call,0,0,8,16);Rect(call,1,8,8,16);
  s.currentFont.Size=12;Draw(s,"Q中",big,small);Check(Graphics.calls.Count==2,"mixed original and bitmap draws");
  var original=Graphics.calls[0];Check(original.material==s.currentFont.font.material,"original material retained");Equal(original.mesh.vertices[0].x,1,"original minX retained");Equal(original.mesh.vertices[0].y,-2,"original minY retained");Equal(original.mesh.vertices[2].x,11,"original maxX retained");Equal(original.mesh.vertices[2].y,10,"original maxY retained");
  return "PASS: actual renderer native 12/6 and 16/8 geometry, atlas selection/UVs, baseline, original glyphs and render cleanup";
 }
}
