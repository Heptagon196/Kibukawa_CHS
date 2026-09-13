using System;
using System.Text;
using Kibukawa8.Runtime;

public static class NativeDialogueLayoutTests
{
    private static void Check(bool value, string message) { if (!value) throw new Exception(message); }
    private static RuntimeRow Row(string text)
    {
        var colors = new byte[text.Length];
        var controls = new byte[text.Length];
        for (int i = 0; i < text.Length; i++) { colors[i] = (byte)(i % 8); controls[i] = (byte)(i % 5 == 0 ? 46 : 0); }
        return new RuntimeRow { SourceText = "original", Text = text, Colors = colors, Controls = controls, RubyJson = "{}" };
    }
    private static void Preserved(RuntimeRow original, RuntimeRow[] wrapped)
    {
        var text = new StringBuilder(); int offset = 0;
        foreach (var row in wrapped)
        {
            text.Append(row.Text);
            Check(row.SourceText == original.SourceText && row.RubyJson == "{}", "Source and disabled ruby must survive wrapping");
            for (int i = 0; i < row.Text.Length; i++, offset++)
            {
                Check(row.Colors[i] == original.Colors[offset], "Wrapping changed a color");
                Check(row.Controls[i] == original.Controls[offset], "Wrapping moved or lost a control");
            }
        }
        Check(text.ToString() == original.Text, "Wrapping changed text or whitespace");
    }
    public static void Run()
    {
        string choice = Kibukawa.Engine.Gmode20050817.NativeDialogueLayout.PrepareChoiceText("从１２楼被害者家中的阳台");
        Check(choice == "从　１２　楼被害者家中的阳台", "Choice requires both boundaries, no blank inside digits");
        Check(Kibukawa.Engine.Gmode20050817.NativeDialogueLayout.PrepareChoiceText(choice) == choice, "Choice spacing idempotence");
        Check(Kibukawa.Engine.Gmode20050817.NativeDialogueLayout.PrepareChoiceText("从3楼") == "从　3　楼", "Single digit boundaries");
        Check(Kibukawa.Engine.Gmode20050817.LatinMetrics.Width('１') == 9, "Choice halfwidth digit");

        var notebook=Kibukawa.Engine.Gmode20050817.NativeDialogueLayout.PrepareNotebookRows(new[]{
            Row("艾纳"),Row("２２岁"),Row("IT工程师"),Row("参与MO调查，2003 年开始。")});
        Check(notebook.Length==4 && notebook[0].Text=="艾纳", "Notebook field boundaries changed");
        Check(notebook[1].Text=="２２　岁", "Notebook age spacing missing or digits split");
        Check(notebook[2].Text=="IT　工程师", "Notebook occupation spacing missing");
        Check(notebook[3].Text=="参与　MO　调查，2003 年开始。", "Notebook prose spacing or existing blank changed");
        Check(notebook[1].Controls[0]==46 && notebook[1].Controls[2]==0, "Notebook spacing moved controls");
        Check(Kibukawa.Engine.Gmode20050817.LatinMetrics.NotebookWidth('　',13)==6 &&
            Kibukawa.Engine.Gmode20050817.LatinMetrics.NotebookWidth('２',13)==7, "Notebook space/digit advances");
        Check(Kibukawa.Engine.Gmode20050817.NativeDialogueLayout.PrepareNotebookRows(notebook)[3].Text==notebook[3].Text,
            "Notebook spacing must be idempotent");
        var slashRows=new[]{Row("莉绪：“所以想请你根据便条"),Row("提供的线索，"),Row("猜出犯人的生日＞ｏ＜”")};
        foreach(var r in slashRows) {Array.Clear(r.Controls,0,r.Controls.Length);Array.Clear(r.Colors,0,r.Colors.Length);}
        slashRows[0].Controls[slashRows[0].Text.Length-1]=47;
        slashRows[1].Controls[slashRows[1].Text.Length-1]=47;
        slashRows[2].Controls[slashRows[2].Text.Length-1]=59;
        var slashWrapped=Kibukawa.Engine.Gmode20050817.NativeDialogueLayout.Wrap(slashRows);
        Check(!Array.Exists(slashWrapped,r=>r.Text=="条") && slashWrapped[1].Text.StartsWith("条提供的线索"),"Native slash breaks must reflow without isolating 条");
        Check(String.Join("",Array.ConvertAll(slashWrapped,r=>r.Text))==String.Join("",Array.ConvertAll(slashRows,r=>r.Text)),"Slash reflow lost text");
        for(int i=0;i<slashWrapped.Length;i++)for(int j=0;j<slashWrapped[i].Controls.Length;j++)
            Check(slashWrapped[i].Controls[j]==0 || j==slashWrapped[i].Controls.Length-1,"Slash cannot skip remaining text within a row");
        Check(slashWrapped[slashWrapped.Length-1].Controls[slashWrapped[slashWrapped.Length-1].Text.Length-1]==59,"Final click boundary changed");
        var face=Row("莉绪：“你好呀（⌒∇⌒）”");
        var faceRows=Kibukawa.Engine.Gmode20050817.NativeDialogueLayout.Wrap(new[]{face});
        Check(Array.Exists(faceRows,r=>r.Text.Contains("（⌒∇⌒）")),"Screenshot kaomoji must stay on one row");
        Preserved(face,faceRows);
        foreach(string expression in new[]{"(^_^)" ,"（╬ﾟ皿ﾟ）", "（⌒ ∇ ⌒）", "^^"}) {
            var sample=Row("一二三四五六七八九十甲"+expression+"。”");
            var output=Kibukawa.Engine.Gmode20050817.NativeDialogueLayout.Wrap(new[]{sample});
            Check(Array.Exists(output,r=>r.Text.Contains(expression)),"Face split: "+expression);
            Preserved(sample,output);
        }
        var wideFace=Row("（⌒∇⌒）");
        var narrowRows=Kibukawa.Engine.Gmode20050817.NativeDialogueLayout.Wrap(new[]{wideFace},2);
        Preserved(wideFace,narrowRows);
        Check(narrowRows.Length>1,"Overwide faces must still make progress within narrow layouts");
        foreach(string expression in new[]{"＞ｏ＜","♪（⌒∇⌒）", "（⌒∇⌒）","^^","⌒▽⌒","（＞＿＜）","（´≦｀）ノ","＞＿＜","（⌒▽⌒）ノ","（｀皿´）","ヾ（≧Δ≦）ノ","（⌒∇⌒）／","（≧∀≦）ノ","^^；","ｍ（＿　＿）ｍ","（｀益´）","＾＾；","（⌒∇⌒；","⌒∇⌒","＊⌒∇⌒＊","ｏ⌒∇⌒ｏ","（＾ー＾）","（⌒ー⌒；","ｏ⌒－⌒ｏ","（｀∇´）","（⌒∇⌒","（⌒－⌒；","＾ω＾","⌒－⌒；","・ω・","（・ω・）","⌒∇⌒；","（￣∇￣）／","（´～｀；","（｀д´）ノ","（｀皿´）ノ","（＠ω＠","（＠ω＠；ノ","＠ω＠）","＼（＞ω＜）／","Σ（＠ω＠","（｀ω´；","Σ（＠ω＠Ξ　Ξ＠ω＠）","（×ω×；","（￥ω￥☆","（・ω⊂","（；ω；","（｀ω´","（・ω・）ノ","（´ω｀；","（￣ω￣","（＾ω＾","（・ω・","（×ω×","ΣΣ（◎ω◎ノノ","＠ω＠","（⌒∇⌒）ｂ","（⌒ー⌒）ｖ","⌒ー⌒","（￣＾￣；","（；ω；）","（＾ω＾；","（－ω－","〈（｀ω´）／","Σ（◎ω◎","＼（｀ω´）〉","（＞ω・）ｂ","＾＾"}) {
            int faceWidth=0;foreach(char c in expression)faceWidth+=Kibukawa.Engine.Gmode20050817.LatinMetrics.Width(c);
            for(int prefix=0;prefix<13;prefix++) {
                var sample=Row(new string('。',prefix)+expression+"。");
                var output=Kibukawa.Engine.Gmode20050817.NativeDialogueLayout.Wrap(new[]{sample});
                if(faceWidth<=204) Check(Array.Exists(output,r=>r.Text.Contains(expression)),"Corpus face split at "+prefix+": "+expression);
                Preserved(sample,output);
            }
        }
        var mixed=Row("第３章M2的编号，ABC123。已有 2 个");
        var spaced=Kibukawa.Engine.Gmode20050817.NativeDialogueLayout.Wrap(new[]{mixed},127)[0];
        Check(spaced.Text=="第　３　章　M2　的编号，ABC123。已有 2 个", "Only adjacent Han/Latin boundaries need a space");
        int originalIndex=0;
        for(int i=0;i<spaced.Text.Length;i++) {
            if(spaced.Text[i]=='　') { Check(spaced.Controls[i]==0,"Inserted blanks cannot trigger VM events"); continue; }
            Check(spaced.Text[i]==mixed.Text[originalIndex] && spaced.Colors[i]==mixed.Colors[originalIndex] &&
                spaced.Controls[i]==mixed.Controls[originalIndex],"Spacing must preserve original characters, colors and controls");
            originalIndex++;
        }
        Check(Kibukawa.Engine.Gmode20050817.NativeDialogueLayout.Wrap(new[]{spaced},127)[0].Text==spaced.Text,"Spacing must be idempotent");

        var m2=Kibukawa.Engine.Gmode20050817.NativeDialogueLayout.Wrap(new[]{Row("轰动鞠滨的Ｍ２究竟是什么？")});
        Check(String.Join("",Array.ConvertAll(m2,r=>r.Text))=="轰动鞠滨的　Ｍ２　究竟是什么？","Screenshot M2 must have exactly one separator on each side");
        var shortNote=Row("好。（译注：说明。）");Array.Clear(shortNote.Controls,0,shortNote.Controls.Length);shortNote.Controls[shortNote.Text.Length-1]=46;
        var inline=Kibukawa.Engine.Gmode20050817.NativeDialogueLayout.WrapWithAnnotations(new[]{shortNote},12,4);
        Preserved(shortNote,inline);
        var longNote=Row("“这家公司名字挺像，规模却差远了呢。”（译注：两个公司名称的日语读音开头相同，因此说名字相似，中文译名无法直接体现这层联系。）");
        Array.Clear(longNote.Controls,0,longNote.Controls.Length);longNote.Controls[longNote.Text.Length-1]=46;
        var split=Kibukawa.Engine.Gmode20050817.NativeDialogueLayout.WrapWithAnnotations(new[]{longNote},12,4);
        Check(String.Join("",Array.ConvertAll(split,r=>r.Text))==longNote.Text,"Long note must remain visible dialogue text");
        int pauses=0;foreach(var r in split)foreach(byte c in r.Controls)if(c==59)pauses++;
        Check(pauses==1 && split[split.Length-1].Controls[split[split.Length-1].Text.Length-1]==46,"Long note needs one native click before annotation, then original terminal wait");
        var english=Row("Ｍａｓｋｅｄ　Ｍｕｒｄｅｒｅｒ");
        var latin=Kibukawa.Engine.Gmode20050817.NativeDialogueLayout.Wrap(new[]{english},12);
        Check(latin.Length==1,"Masked Murderer must fit on one line at native halfwidth");
        Preserved(english,latin);

        RuntimeRow first=Row("是的，我们也根据伤口的深度"), next=Row("和角度考虑过这一点……");
        Array.Clear(first.Controls,0,first.Controls.Length);Array.Clear(next.Controls,0,next.Controls.Length);
        next.Controls[next.Controls.Length-1]=46;
        var joined=Kibukawa.Engine.Gmode20050817.NativeDialogueLayout.Wrap(new[]{first,next});
        Check(joined.Length==2 && joined[1].Text.StartsWith("度和角度"),"Old line boundary must not isolate 度 from 和角度");
        Check(String.Join("",Array.ConvertAll(joined,r=>r.Text))==first.Text+next.Text,"Joining lost dialogue text");
        int offset=0;foreach(var row in joined) foreach(byte color in row.Colors) {
            Check(color==(offset<first.Text.Length?first.Colors[offset]:next.Colors[offset-first.Text.Length]),"Joining moved color");offset++;
        }
        Check(joined[joined.Length-1].Controls[joined[joined.Length-1].Text.Length-1]==46,"Joining lost final wait control");
        first.Controls[first.Text.Length-1]=46;
        Check(Kibukawa.Engine.Gmode20050817.NativeDialogueLayout.Wrap(new[]{first,next}).Length==3,"Native wait boundary must not be merged");
        var clause=Row("这是前一句，");Array.Clear(clause.Controls,0,clause.Controls.Length);clause.SourceText="前の文、";
        Check(Kibukawa.Engine.Gmode20050817.NativeDialogueLayout.Wrap(new[]{clause,next})[0].Text==clause.Text,"Bilingual punctuation break must remain");
        RuntimeRow heading=Row("刑警"), speech=Row("“是的。”");
        Array.Clear(heading.Controls,0,heading.Controls.Length);Array.Clear(speech.Controls,0,speech.Controls.Length);
        for(int i=0;i<heading.Colors.Length;i++) heading.Colors[i]=2;
        Array.Clear(speech.Colors,0,speech.Colors.Length);
        Check(Kibukawa.Engine.Gmode20050817.NativeDialogueLayout.Wrap(new[]{heading,speech}).Length==2,"Colored speaker heading must remain separate");
        RuntimeRow creditFirst=Row("关本俊"), creditSecond=Row("吉江一晓");
        creditFirst.SourceText="関　本　俊";creditSecond.SourceText="吉　江　一　暁";
        Array.Clear(creditFirst.Controls,0,creditFirst.Controls.Length);Array.Clear(creditSecond.Controls,0,creditSecond.Controls.Length);
        Check(Kibukawa.Engine.Gmode20050817.NativeDialogueLayout.Wrap(new[]{creditFirst,creditSecond},127).Length==2,
            "Source-spaced credit rows must remain separate even when translated names are compact");
        RuntimeRow chapter=Row("第1章"), subtitle=Row("“面具的世界”");
        chapter.SourceText="第１章";subtitle.SourceText="「仮面の世界」";
        Array.Clear(chapter.Controls,0,chapter.Controls.Length);Array.Clear(subtitle.Controls,0,subtitle.Controls.Length);
        Check(Kibukawa.Engine.Gmode20050817.NativeDialogueLayout.Wrap(new[]{chapter,subtitle}).Length==2,"Chapter number and subtitle must retain native separate rows");
        var longRow = Row("就这么迷茫着，转眼已过了三个月……");
        var wrapped = Kibukawa.Engine.Gmode20050817.NativeDialogueLayout.Wrap(new[] { longRow });
        Check(wrapped.Length == 2, "Screenshot dialogue must wrap to two native-size rows");
        foreach (var row in wrapped) Check(row.Text.Length * 17 <= 204, "Wrapped line exceeds native 204px width");
        Preserved(longRow, wrapped);
        var punctuation = Row("一二三四五六七八九十甲乙，后续");
        wrapped = Kibukawa.Engine.Gmode20050817.NativeDialogueLayout.Wrap(new[] { punctuation });
        Check(!wrapped[1].Text.StartsWith("，"), "Closing punctuation must not start the next line when a safe break exists");
        Preserved(punctuation, wrapped);
        var title = Row("假　面　幻　影　杀　人　事　件");
        wrapped = Kibukawa.Engine.Gmode20050817.NativeDialogueLayout.Wrap(new[] { title });
        Check(wrapped.Length == 1 && wrapped[0].Text == title.Text, "Spaced title must retain original positions");
        Preserved(title, wrapped);
        var empty = Row("");
        Check(Kibukawa.Engine.Gmode20050817.NativeDialogueLayout.Wrap(new[] { empty }).Length == 1, "Empty original row must be retained");
        var overflow = new RuntimeRow[128];
        for (int i = 0; i < overflow.Length; i++) overflow[i] = empty;
        bool rejected = false;
        try { Kibukawa.Engine.Gmode20050817.NativeDialogueLayout.Wrap(overflow); } catch (InvalidOperationException) { rejected = true; }
        Check(rejected, "VM row-count overflow must be rejected");
    }
}
