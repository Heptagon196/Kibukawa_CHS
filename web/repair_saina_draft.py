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
    return before+'//ha4\n'+work+'//ha5\n'+love+notice+'*s04-sys'+end
