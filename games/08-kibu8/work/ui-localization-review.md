# 第八作界面译稿复核

来源：原始备份 `originals/kibu8_Data/StreamingAssets/localization` 的 `Localization` TextAsset，日文 `ja` 列。15 个非空 CSV 数据记录全部译出；未用英文列替代日文语义。JSON 的 `row` 从 1 计数，不计表头与空行；一条记录内部的换行不增加记录号。原文件 SHA-256 与 path ID 已记录在译稿中。

- `pause_menu_label_close` 日文为“閉じる”，采用“关闭”，不按英文列扩大成“继续游戏”。
- `loading_autosave_msg` 保留原始 CRLF 换行、否定含义及要求使用游戏内存档的提示。
- 排行榜相关 4 行按资源收录译出，是否能从本作正常流程进入尚未实机确认。`ranking_load_ranking_msg` 的 ja 列原为 `Loading...`，译为“加载中……”。
- 15 行均属于玩家界面文本，无技术标识行；行键及语言标识不作为译文改写。

`ui-assembly.zh-CN.json` 是另一份独立的程序集界面译稿，含 97 个精确 IL 位置：66 个常规玩家界面、15 个旧手机服务界面、16 个技术哨兵位置。相同词的重复位置保留，方便使用 token、instruction、source_text 三者校验后处理。只覆盖 CanvasEx 中选出的显示文字、CharacterInput 的确认/删除/确定，以及 WindowDialog 的全屏选项。

- `停止`、`消去`、`全`、`変えないでお願いします`、`ＦＯ` 均是 CanvasEx 的命令或控制值，保留原串。`漢字` 在 CharacterInputKeyManager 中用于分类比较/查表，也保留。它们标为 `technical_sentinel`，不能把分类当作漏译。
- `戻る` 在 CanvasEx::SoftKeyMenu 中也用于比较旧按钮字符串。必须与调用方一致处理，不能只替换可见生产处而遗漏该比较处；已把该位置列入译稿并加注。
- `未登録` 位于 CheckSaveData 的存档信息赋值，译为“空存档”。
- 声音、背景音乐、音效及读取存档选项的前置对齐空白保留；旧服务错误提示尾部的空白不传入中文。旧服务两行提示按同屏语序处理，不当作点击边界。
- `PaintKakin` 中 `ゲームランチ` 是旧服务名，暂译“游戏午餐服务”。相关两个位置明确标为 `provisional_service_name`；未升入公共术语。该旧手机收费/下载流程在移植版是否可达未知，不能宣称无用代码已验证。
- 对 `assembly-strings.json` 全体字符串检索未发现 `Now Loading` 或 `Now Loading...`。没有编造源条目；资源中的 `Loading...` 已在 localization 译稿译出。
- CharacterInput 的假名/汉字输入键表未纳入此次 UI 译稿，因为改动会影响可输入的内容；资产名、分辨率数字、日志和异常信息同样未纳入。

已对照系列指导、公共术语及本作锁定表；本批未发现公共定译冲突，未改公共表及前作译文。静态复核了显示方法及输入键初始化调用，保留 `{0}` 占位符。尚未接入补丁，也未操作游戏窗口；中文显示宽度与实机效果由用户验证。
