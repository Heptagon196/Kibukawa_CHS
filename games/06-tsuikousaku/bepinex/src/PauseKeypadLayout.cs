using System;
using UnityEngine;
using UnityEngine.UI;

namespace Kibu1ZhCN
{
    // Scoped to the sixth game's SettingDialog. Original buttons and animation
    // components stay in their original hierarchy; only their positions change.
    public sealed class PauseKeypadLayout : MonoBehaviour
    {
        private RectTransform root, contents, background, title, panel;
        private Vector2 contentsPosition, backgroundPosition, titlePosition;
        private Vector3 contentsScale, backgroundScale, titleScale;
        private Font font;
        private Vector2 lastSize;
        private const float MenuWidth=856f, Gap=48f, PanelWidth=500f, DesignHeight=640f;

        public static void Attach(Component dialog)
        {
            if (dialog==null || dialog.GetComponent<PauseKeypadLayout>()!=null) return;
            var root=dialog.transform.Find("Dialog") as RectTransform;
            if (root==null || root.Find("Contents")==null || root.Find("BG")==null || root.Find("DialogTitle")==null)
                throw new InvalidOperationException("Unexpected SettingDialog hierarchy");
            dialog.gameObject.AddComponent<PauseKeypadLayout>().Initialize(root);
        }
        private void Initialize(RectTransform value)
        {
            root=value;
            contents=(RectTransform)root.Find("Contents"); background=(RectTransform)root.Find("BG"); title=(RectTransform)root.Find("DialogTitle");
            contentsPosition=contents.anchoredPosition; backgroundPosition=background.anchoredPosition; titlePosition=title.anchoredPosition;
            contentsScale=contents.localScale; backgroundScale=background.localScale; titleScale=title.localScale;
            font=Font.CreateDynamicFontFromOSFont(new[]{"Microsoft YaHei","SimSun"},32);
            panel=Rect("ChinesePhoneKeypad",root,Vector2.zero,new Vector2(PanelWidth,560f));
            var bg=panel.gameObject.AddComponent<Image>();bg.color=new Color(.10f,.14f,.21f,.98f);bg.raycastTarget=false;
            var canvasGroup=panel.gameObject.AddComponent<CanvasGroup>();canvasGroup.interactable=false;canvasGroup.blocksRaycasts=false;
            Label(panel,"手机拼音九键",new Vector2(0,235),new Vector2(480,50),32);
            string[] digits={"1","2","3","4","5","6","7","8","9","*","0","#"};
            string[] letters={"","ABC","DEF","GHI","JKL","MNO","PQRS","TUV","WXYZ","","",""};
            for(int i=0;i<digits.Length;i++)
            {
                var key=Rect("Key"+i,panel,new Vector2((i%3-1)*150,151-(i/3)*96),new Vector2(136,84));
                var image=key.gameObject.AddComponent<Image>();image.color=new Color(.19f,.28f,.38f,1f);image.raycastTarget=false;
                Label(key,digits[i],new Vector2(0,15),new Vector2(130,40),32);
                Label(key,letters[i],new Vector2(0,-23),new Vector2(130,30),25);
            }
            Label(panel,"不计声调，每个字母对应所在键的数字",new Vector2(0,-217),new Vector2(480,32),22);
            Label(panel,"重复字母按出现次数计算",new Vector2(0,-249),new Vector2(480,30),22);
            Apply();
        }
        private static RectTransform Rect(string name,Transform parent,Vector2 position,Vector2 size)
        {
            var rect=new GameObject(name,typeof(RectTransform)).GetComponent<RectTransform>();
            rect.SetParent(parent,false);rect.anchorMin=rect.anchorMax=rect.pivot=new Vector2(.5f,.5f);
            rect.anchoredPosition=position;rect.sizeDelta=size;return rect;
        }
        private void Label(Transform parent,string value,Vector2 position,Vector2 size,int fontSize)
        {
            var text=Rect("Label",parent,position,size).gameObject.AddComponent<Text>();
            text.font=font;text.fontSize=fontSize;text.alignment=TextAnchor.MiddleCenter;text.color=Color.white;
            text.raycastTarget=false;text.supportRichText=false;text.horizontalOverflow=HorizontalWrapMode.Overflow;text.verticalOverflow=VerticalWrapMode.Overflow;text.text=value;
        }
        private void LateUpdate()
        {
            if(root!=null && root.rect.size!=lastSize)Apply();
        }
        private void Apply()
        {
            lastSize=root.rect.size;
            float scale=Mathf.Min(1f,Mathf.Min(Mathf.Max(1,lastSize.x-48)/(MenuWidth+Gap+PanelWidth),Mathf.Max(1,lastSize.y-48)/DesignHeight));
            float menuX=-(PanelWidth+Gap)*.5f*scale;
            contents.anchoredPosition=new Vector2(menuX,contentsPosition.y*scale);contents.localScale=contentsScale*scale;
            background.anchoredPosition=new Vector2(menuX,backgroundPosition.y*scale);background.localScale=backgroundScale*scale;
            title.anchoredPosition=new Vector2(menuX,titlePosition.y*scale);title.localScale=titleScale*scale;
            panel.anchoredPosition=new Vector2((MenuWidth+Gap)*.5f*scale,0);panel.localScale=Vector3.one*scale;
        }
        private void OnDestroy()
        {
            if(contents!=null){contents.anchoredPosition=contentsPosition;contents.localScale=contentsScale;}
            if(background!=null){background.anchoredPosition=backgroundPosition;background.localScale=backgroundScale;}
            if(title!=null){title.anchoredPosition=titlePosition;title.localScale=titleScale;}
            if(panel!=null)Destroy(panel.gameObject);
            if(font!=null)Destroy(font);
        }
    }
}
