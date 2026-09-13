# 第八作序列化界面文本复核

只读扫描 kibu8_Data/StreamingAssets 下全部非 manifest 文件，以及 kibu8_Data 的 *.assets 与 level0。共 25 个文件、6875 个 Unity 对象、1575 个 MonoBehaviour；提取到 101 处日文字符串。加载失败 0；补查仅半角片假名文本为 0。扫描前后 25 个源文件 SHA-256 一致。

按四字节对齐的长度前缀识别有效 UTF-8 字符串，并逐条核对 MonoScript 类名、GameObject 名称与 bundle 类型树。全部候选为 Text.m_Text 或 TitleDataModel.titleData 字段。原始 .assets/level0 类型树不完整，其字段名称由对应预制体布局推定，JSON 已单独标注；字节位置及原文均来自实际资源。

各类记录数：
- existing_localization_duplicate: 21
- player_ui_serialized: 28
- excluded_template: 44
- existing_assembly_duplicate: 4
- excluded_debug_ui: 4

新增玩家文本（同名资源副本共用以下译文）：

- 探偵・癸生川凌介事件譚 / Vol.8「仮面幻影殺人事件」 → 侦探·癸生川凌介事件谭 / 第八作《假面幻影杀人事件》
- ジャンル：推理アドベンチャー / 幻影に抱かれ、私は仮面をかぶる… / 仮想世界と現実世界で絡み合う、謎の連続殺人事件。 → 类型：推理冒险 / 幻影将我拥入怀中，我戴上了假面…… / 虚拟世界与现实世界相互交织的神秘连环杀人案。
- ウィンドウ設定 → 窗口设置
- 入力して下さい → 请输入
- 操作説明 → 操作说明
- 前編をプレイ → 开始前篇
- プレイヤー名 → 玩家名称
- 後編をプレイ → 开始后篇
- ゲームを終了する → 退出游戏
- 導入編をプレイ → 开始序篇
- ＜ゲーム画面＞ → ＜游戏画面＞

排行榜的“プレイヤー名”位于 ListName(Text)，是列标题，保留翻译；“１プライヤー名”位于 PlayerName(Text)，是行样例，排除。“ランキング名”是动态标题占位。“ボタン名”和“説明１６字…”是操作说明模板；不把它们冒充最终说明内容。debugmenu 的存档清除和时间缩放明确排除。原样扫描未发现需要翻译的内部标识字段。

localization 与托管字面量重复项逐位置列出并复用对应译文，分类区分为 existing_*_duplicate，避免误认为新增内容。新增标题、宣传简介来自 TitleDataModel 的日语配置，不能用 titleDataEn 的 Archives Title 占位替代。

byte_offset 指对象内部 UTF-8 正文偏移，length_prefix_offset 是前四字节长度，serialized_byte_offset 指解压后的 SerializedFile 内偏移。对于 Unity bundle，不能拿这个偏移直接改外层压缩文件。本次仅提供待构建文本，未修改或运行游戏，未确认窗口显示、字体与流程可达性。
