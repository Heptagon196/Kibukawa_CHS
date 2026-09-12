# 第七作汉化交付状态

作品副标题：**林居刑警的搜查笔记**（用户确认）。“小小名侦探”用于开场文字、第三章名称及标题图底部小字“－小小名侦探－”，不并入正式游戏名。

2026-09-12：用户完成实机验收并确认汉化完成，授权发布1.0.0。开发侧完成离线构建和校验，未自行启动或操作游戏窗口。

2026-09-11：四章正文、三个辅助脚本及已提取的有效文字界面全部译入，完成译者自审、独立逐单元复审及协调校订。原始5653条记录中，3233条已处理、2420条经审查排除、待译0条。原先3231个候选补入6条ASCII加载/声音标签，再排除4条标题模板，得到3233条；未通过扩大排除掩盖未译正文。

## 审校与检查

- 1332个点击单元逐单元对照，98个着色段保持强调对象和执行边界。
- 原游戏重新解析8743条指令，指令、跳转和来源定位与提取清单一致。
- 终章2×2钥匙组合与4×4×4时间/地点/动作组合共68种完成结构与中文拼接核对；正确答案回跳共用尾句保留。
- 19个固定页面单元另行复核：章节标题、地点卡、操作标题及片尾角色/姓名分行；日文注音槽用空串保留指令。无实机布局通过声明。
- 同色段内分配文本，禁止跨颜色、指令或分支共用尾句分摊。39条本作锁定术语已归入公共表，暂不影响任何前作译文。
- 唯一保留的假名为公共表批准的旧服务名称ｽｰﾊﾟｰｹﾞｰﾑﾗﾝﾁ。其余文字译稿未检出假名残留。
- 公共文字风格检查保留63个已逐项复核候选：56个固定排版空白/缩进提示、7个动态互斥分支引号提示。未关闭检查规则；本作验证器要求候选与已审源译逐项相同。
- 重复extract确认cache和manifest逐字节不变；原文件指纹及前六作工程均通过未变核验。

四页图片操作说明已按44条中文内容重新排版并接入补丁，见images/help-pages.translation.json。输入界面四种字符类别已接入显示替换，原逻辑字符串保持不变，映射见bepinex/display-labels.json。

## 当前交付范围

现已接入运行时文字挂钩、中文字体、标题图、四页帮助及公共图片/历史记录插件，0.1.0测试补丁已经安装并由用户验证，现以1.0.0发布。enabled=true，release_ready=true；开发侧没有启动或操作游戏窗口。当前构建及安装结果分别见reports/bepinex_latest.json与reports/installation_latest.json。

公共engine/bepinex构建层已在启动阶段完成Kibu7Bootstrap探针验证；继续复用gmode-v1，不新增adapter。不改原游戏字节码、音量处理或存档头。

## 复现

首次克隆的完整依赖与重建流程见[README.md](README.md)。先恢复原文快照，再在系列根目录执行：

```powershell
.venv/Scripts/python.exe games/07-otonari/scripts/validate_translation.py
.venv/Scripts/python.exe tools/series.py click-check --game kibu7 --strict
.venv/Scripts/python.exe tools/series.py status --game kibu7
```

正式对话译稿为work/dialogue-tagged.json，缓存为work/cache.json；新改动必须重审受影响的点击与颜色基线。本作已启用，用户于2026-09-12确认汉化完成；启用、离线检查和用户实机验收分别记录。

完整审校依据：review/translation-integration.json、review/fixed-page-review.json、review/fixed-pages.independent.json、review/color-spans.reviewed.json、review/text-style.reviewed.json及work/click_boundaries.reviewed.json。全文中日对照可读稿在translated_texts/。

## 公共术语检查问题已修复

按用户要求，以第六作实际使用的本地表为准同步公共表：七个人名、鱼铺谜题条目、拼音九键规则及来源哈希。未修改第六作或其他前作正文译文、本地表。历史问题与修复记录见review/preexisting-series-glossary-issue.json。

修复后公共术语检查通过（394条来源引用），第六作scn1术语筛选无冲突，第七作全文离线校验通过。修改前后核对196个本地表、缓存及译稿文件，内容未变。

## 安装结果

0.1.0已安装到GmodeArchivesPlus_kibu7：46个安装文件及176个原始文件哈希逐一核验通过。开发侧没有启动游戏；用户已完成实机验证。此处为0.1.0安装历史，1.0.0发布包由最新构建及发布清单记录，不据此宣称1.0.0已经重新安装。安装备份与完整清单见reports/installation_latest.json。

## 搜查笔记全屏布局修复

搜查笔记按原始换行保留标题、空行和六条线索，64种线索状态逐一回放通过。全屏正文使用实际九行容量，不再套用底部五行分页。回归包含第十行安全等待和底部对话原容量，8355项断言通过。详见review/notebook-layout-fix.json。
