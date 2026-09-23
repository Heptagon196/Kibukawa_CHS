"""Small, documented navigation repairs to the author's unfinished fifth chapter.

No new fictional dialogue: absent branches explicitly say the original stops here.
"""
def repair(text, filename):
    if filename != 's05.adv':
        return text
    boundary = text.index('//------------------------------------------------------------')
    text = ('[BGSet pic=""][TransAll eff="fade" t=0]\n[Talker char="３" SE=off]\n'
            '（汉化说明）[r]原作正式流程到此结束。[r]文件中另附有第五章的未完成草稿。[pp]\n'
            '[Talker char=""]\n是否继续阅读第五章草稿？[r]\n[YesNo]\n'
            '[DelButton group=yn]\n'
            '[Goto label="start" _cond_="@SelectYN == \'YES\'"]\n'
            '[Goto path="./script/first.adv"]\n'+text[boundary:])
    # The draft swaps the work/love headings, duplicates the work label, and uses
    # ha4 for both branches. Route each existing conversation to its actual topic.
    before, love = text.split('//ha4\n', 1)
    love, after = love.split('//ha5\n', 1)
    love = love.replace('s04-話-仕事', 's04-話-恋愛').replace('ha4', 'ha5')
    work, end = after.split('*s04-sys', 1)
    work = work.replace('s04-話-恋愛', 's04-話-仕事').replace('ha5', 'ha4')
    love = love.replace('text="交谈>关于澪的工作"', 'text="交谈>关于澪的恋爱"')
    work = work.replace('text="交谈>关于澪的恋爱"', 'text="交谈>关于澪的工作"')
    # Unfinished prose notes originally run into a Goto and disappear. Present
    # their translated content as narration, with an explicit source boundary.
    work = work.replace('并尽量提供贴心的服务。\n', '并尽量提供贴心的服务。[pp]\n[Talker char=""]\n')
    work = work.replace('随时向各处下达指示，确保服务周到。\n',
                        '随时向各处下达指示，确保服务周到。[ppp]\n')
    work = work.replace('我很佩服。她说：“其实我会记笔记。”\n',
                        '我很佩服。她说：“其实我会记笔记。”[pp]\n')
    # The original exposes an unwritten topic once the conversation flag unlocks.
    notice = ('*s04-話-\n[Talker char=""]\n'
              '（汉化说明：原作此处尚未完成，\n[r]没有公开后续剧情。）[pp]\n'
              '[Goto label="s04"]\n\n')
    result = before+'//ha4\n'+work+'//ha5\n'+love+notice+'*s04-sys'+end
    anchor = '[Cmd CmdText="（调查记录）" GotoLabel="s04-sys"]'
    assert result.count(anchor) == 1
    # The last draft scene has no progression branch. Show this only while its
    # main menu is open; CmdOn clears message layers before any conversation.
    footer = ('[ClearMsg id=6]'
              '[MsgLayer id=6 visible=true posX=0 posY=454 width=640 height=26 '
              'margin_Left=20 margin_Top=0 font_Size=16 font_Color=0xcccccc '
              'font_Name="Saina Noto" font_Embed=false speed_Normal=0 sound_Char="" '
              'alpha_All=100 edge_Visible=false]'
              '[Output id=6 msg="此场景后没有新内容，无法推进。"]')
    return result.replace(anchor, anchor + footer)
