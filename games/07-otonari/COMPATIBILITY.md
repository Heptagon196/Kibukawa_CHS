# 第七作接入记录

作品副标题《音成刑事の捜査メモ》，用户确认中文为《林居刑警的搜查笔记》。scn0 条目18另有开场正文“ちいさな名探偵”（译为“小小名侦探”），标题图底部亦保留“－小小名侦探－”，不纳入正式游戏名。林居姓氏沿用系列公共定译。

安装路径 `../../GmodeArchivesPlus_kibu7`，项目路径 `games/07-otonari`，均相对 series.json。现已启用本作构建安装，运行时接入和离线布局验证已完成；用户于2026-09-12完成实机验收并确认汉化完成，授权发布1.0.0。开发侧未启动或操作游戏窗口。下文提取与探针部分保留初次接入记录。

## 引擎结论

Unity Mono / Windows x64，资源包 otonari.res。继续复用 gmode-v1；未新增 adapter，未修改公共构建层或前作工程。后续全屏正文分页修复已进入公共gmode-v1的DialogueReflow.cs，按实际可用行数计算；搜查笔记固定布局留在本作FixedCardLayout.cs。

以已核验原文件指纹的前六作分别对照；最近的第六作与本作 CanvasEx 共有56个方法，规范化 appli1 命名空间和协程编号后46个方法体一致、10个不同，新增 Vol，无缺失方法。对照含局部变量和异常处理。

Read、Jump、ExeText 与 Script 协程一致，SJIS字符表、指令定义一致。差异不在正文指令协议：

- 新增 Volume / KEY_SOFT2，按键数组与 KeyF 由7项改为8项；新增四档音量控制和软键显示，Play/Mute使用 Volume×25。
- Init读取音量，Adv的相关读取跳过字节数1→2，Save写入位置6→7。不得复用前作存档头偏移或整段覆盖Adv/Init。
- Idle/IdleCoroutine增加音量键处理，IdleCoroutine还有时钟回退处理。
- Paint仅图片定位常数22→17、40→41；资源名、音频表和默认音频索引变化。
- RVA差异是KeyF初始化表28→32字节，不是SJIS字符表变化。

详见 engine-review.json；完整六作对照可用 scripts/compare_engine.py 重建至 research/normalized-engine-comparison.json。以上支持复用文字adapter，不表示本作完整运行时挂钩或画面已经验收。

## 提取与构建

已提取scn0–scn3、三个subscn、localization、序列化UI与程序集字符串；共5647条，其中3231条待译候选、2416条技术/模板排除候选。排除候选仍须按本作语境检查，不直接当作不可见文本。共1332个静态点击单元。

独立原文快照、来源指纹、定位清单和原始指令回放已建立。提取与探针构建通过前六作工程逐文件哈希不变检查及第七作原始文件不变检查。

公共 engine/bepinex/build.py 已成功编译、组包并校验 Kibu7Bootstrap.dll，进程过滤 kibu7.exe，复用公共core、字体和菜单源码。输出明确标为 NOT_TRANSLATION，无汉化挂钩，未安装。报告位于 reports/bootstrap_latest.json。

## 当前翻译与复现

文字翻译与逐单元审校已完成，当前详细进度和检查命令见[TRANSLATION_STATUS.md](TRANSLATION_STATUS.md)。原候选补入6条ASCII标签、排除4条无效标题模板后，实际3233条已处理；1332点击单元和98着色段均有本作审校记录。标签中的本作hard-break保留固定页面行和动态答案共用尾句；不修改原字节码。

运行时挂钩、字体、标题与四页帮助组包已接入，1.0.0发布状态为enabled=true，release_ready=true。开发侧没有启动或操作游戏窗口；用户已完成实机验收。
