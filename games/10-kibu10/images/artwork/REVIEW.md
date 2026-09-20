# 第十作标题与场景美术汉化审阅

工具：内置 `image_gen`，text-localization 编辑模式。原图均先经 `view_image` 检视。没有用 Python 或代码改图、缩放、拼接。生成尺寸大于游戏原图，运行时适配由图片接入层负责。

## 对照与当前文件

| 原图 | 汉化文件 | 原尺寸 | 输出尺寸 | 文字 |
|---|---|---|---|---|
| inventory/008-titleimage.png | titleimage-zh.png | 354×354 | 1254×1254 | 侦探·癸生川凌介事件谭 |
| inventory/042-title1.png | title1-zh.png | 240×240 | 1254×1254 | 系列名；开始／玩法说明／附加内容；©Andjoy |
| inventory/065-title2.png | title2-zh.png | 240×240 | 1254×1254 | 系列名；开始／玩法说明／附加内容；后篇；原版权 |
| inventory/333-title.gif.png | title-scratch-zh.png | 240×240 | 1254×1254 | 系列名；开始／玩法说明／附加内容；原版权 |
| inventory/241-bg21.jpg.png | bg21-zh.png | 240×116 | 1804×872 | 搜查一课 |

## 审阅说明

- 标题主字「永劫会事件」无需改字，要求保持红色书法、符号、边框与原位置。
- title1 初稿把版权符号画成 @，已弃用；后续以合格 title2 派生并保留 ©Andjoy。
- titleimage 初稿出现透明杂边，已弃用；重试版本为纯黑背景、素白系列名。
- 菜单最初使用「开始游戏／游戏说明」，收到项目锁定词后定向修改为「开始／玩法说明」。mapping.json 列出的文件为最终版本；locked 与 generated 文件仅过程留档。
- bg21 左侧微小字画在原图中不可辨，作为装饰保留；右侧可辨牌匾已改为「搜查一课」。
- 图像生成对原版笔画与背景纹理有轻微重绘，不能声称像素级保真；需由用户实机确认显示和选中动画重叠情况。

## 最终提示词内容

通用限制：只翻译图片内指定文字，保持原图布局、黑底、红色书法与装饰、版权、各元素位置；不添加新内容，保留低分辨率游戏美术风格。

titleimage：`Translate ONLY the thin white vertical text on right. Exact new text top to bottom: 侦 探 · 癸 生 川 凌 介 事 件 谭. Final character 谭 must have 讠 radical, NOT 言. Keep thin plain white font, absolutely no outline, shadow, glow, or decoration. Keep every other component exactly as reference: pure black opaque background, red 永劫会事件 calligraphy, thin red polygon border and red symbol. Retain same composition and margins. The reference is low-resolution retro game artwork, not a request for redesign. Black background must be fully opaque. Do not generate transparent fringes or artifacts.`

菜单图最终编辑：`Make ONLY these exact text corrections on upper-left menus. Rightmost red vertical menu column currently 开始游戏 must become just two vertically stacked characters 开始. Its top remains in same place; remove 游戏 below and restore backdrop. Middle red vertical menu currently 游戏说明 must become four vertically stacked characters 玩法说明. Leftmost 附加内容 unchanged. Preserve positions of all columns. Preserve every other element including copyright, right subtitle 侦探·癸生川凌介事件谭, large 永劫会事件 red title, original ornaments. No other changes.` title2 另要求保留后篇，title1 版权 ©Andjoy，title.gif 版权 ©2005 GENKI & ©Genki Mobile。

bg21：`Use case: text-localization. Edit only the four black calligraphy characters on the framed plaque on the upper right wall of this small 240x116 game background. Replace text 捜査一課 with the four exact simplified Chinese characters 搜查一课 read left to right. Keep plaque shape, frame, paper color and four character spacing, black brush lettering. Preserve every other component exactly: blue sofa foreground, cream walls, left plant, left wall small decorative calligraphy, perspective, muted low-resolution artwork. Do not add anything, do not change framing or dimensions ratio.`


最终交叉审校后，titleimage 末字「谭」与 bg21 末字「课」用 imagegen 定向更正为更清楚的两笔讠；title2 年份分隔符更正为白色短横线；title-scratch 版权更正为 ©2005 GENKI & Genki Mobile。对应最终提示词为只改该字/符号且保留其他所有内容，讠明确描述为单点和横折提，不含言旁的多横及口框。最终五个文件均按 mapping.json 名称就位。
