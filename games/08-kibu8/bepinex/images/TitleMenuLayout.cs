using System;

namespace Kibu8ZhCN.Images
{
    public static class TitleMenuLayout
    {
        public const int Left=(240-109)/2;
        public static bool ClearBackgroundPixel(int x,int y) { return x>=0 && x<240 && y>=145 && y<212; }
        public static int Row(int index)
        {
            switch(index) { case 0:return 151; case 1:return 171; case 2:return 192; default:throw new ArgumentOutOfRangeException("index"); }
        }
        // Ignore the red glow; preserve and dim the white antialiased lettering.
        public static byte NormalChannel(byte r,byte g,byte b) { return (byte)(Math.Min(r,Math.Min(g,b))*2/3); }
        public static bool CanDraw(int state,int selection) { return state!=1 && state!=11 && selection>=0 && selection<3; }
    }
}
