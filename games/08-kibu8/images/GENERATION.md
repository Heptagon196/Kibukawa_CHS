# 第八作标题图

使用内置 image_gen，text-localization 模式。最终提示要求保留 CRT 电视机、胶片背景、白色描边标题、绿色英文副标题，只将系列名改为“侦探·癸生川凌介事件谭”，标题改为“假面幻影杀人事件”，篇章依次为“序篇/前篇/后篇”，菜单为“开始游戏/继续游戏/选项”。菜单高亮单独生成三行黑底红光精灵图。高分辨率生成结果保存在 generated/，仅作等分裁剪及游戏原生尺寸重采样；菜单裁切黑色留白以匹配原生字体高度。

成品：title-0/1/2-zh.png（240×240）、title-menu0/1/2-zh.png（109×17）、titleimage-zh.png（354×354）。资源原图及篇章对应关系均从原 resources.assets 验证。未操作游戏窗口。

## 0.3.2 标题字形修正

内置 image_gen 以三张标题图分别为编辑目标，只纠正主标题第五字为简体“杀”（U+6740），要求保持原构图、配色、菜单和篇章位置；三份高分辨率结果保存在 generated/title-0/1/2-corrected.png，经原生240×240重采样保存为 title-0/1/2-zh.png，并分别目视复核字形。最终提示要点：Precisely edit this game title screen. Main title must be exactly 假面幻影杀人事件. Correct ONLY the fifth character to standard simplified Chinese 杀 U+6740; NOT 殺/染/桑. Preserve square layout, background, menus and chapter label 序篇/前篇/后篇. Match existing fill and white outlined Song/Mincho title style; no redesign.

## 0.3.5 设置背景

通过原PaintMenu的Image_Menu[0]及加载路径确认 scratch1.dat 中 option.jpg（240×240）。内置image_gen提示：仅将右上倾斜便签“環境設定”替换为简体“环境设置”，保留黑板、粉笔网格、图钉、角度、布局，不添加文字；输出重采样至原尺寸并目视复核。高分辨率原稿 generated/option-zh.png，最终 option-zh.png。replacements.json新增CanvasEx.LoadGraphic#*@option.jpg，构建解析scratch1的名称、偏移、长度及资源哈希验证后打包。

## Command icons (0.4.7)

## 0.5.0 字库

12px 界面及指令图标统一使用固定提交的 Z Labs Pixel 12px M CN 原始 KBITX 字形。像素、字距、边界与基线保留；正文仍用 16px Unifont。指令图标每字12px，两个字占24px，原图标上部保持不变。下载脚本校验大小和 SHA256，源字库不进 Git 或发布包，完整 OFL 许可随包附带。

## 0.5.1 行动按钮恢复

按用户反馈，行动按钮图片恢复原先 10px Fusion Pixel 标签、每侧2px留白、原图案和两种状态。此依赖仅用于生成按钮图片；12px 动态界面继续使用 Z Labs，正文仍是16px Unifont。

## 职业专用笔记背景

job_office、job_station、job_mole 三张原始208×88图片也含资料标签。构建保留左侧100列场景像素，右侧复用已汉化memo-profile面板，逐像素验证两部分与各自来源一致，并核对三章节原图相同。三个Image_createImage路径均纳入替换，原游戏资源不改。

## 0.5.3 用户确认的按钮描边样式

所有十个按钮采用原生10px字形和一像素四方向描边，不再填充整条深色底。command-backgrounds.png 是已确认预览中使用的无字底图；构建只取底部内部区域，并映射回各原图调色板，保留原图上部及左右边缘。两种状态均与用户确认的全十按钮10px预览核对。

## 0.5.10 标签统一

人物、笔记统一18×40，同款边框、字重及排版，仅分类配色不同。image_gen同图生成两张成套标签，裁切后缩至原生尺寸。隐藏状态严格复制各成品左侧8×40像素，分别放在背景(8,13)/(8,55)，纸边右侧不改；不另绘、不变形、不另调色。memo_l02原资源18×32仍需指纹和源尺寸校验，仅指定该路由允许替换为18×40。两个标签使用同一张配对原稿images/generated/memo-tabs-equal.png。

## 0.5.13 标签透明遮罩

构建直接从原资源 memo_l01.gif 恢复18×40透明遮罩；与原memo_l02.gif上下边缘核对一致。保留成品全部RGB像素，仅恢复左上、左下共6个透明像素。隐藏状态仍取各成品左侧8列，通过alpha合成到背景，透明角露出原背景，不再留下白角。每次构建校验原尺寸、两种原图的角遮罩和RGB不变。

## 0.5.14 四角透明

纠正0.5.13仅恢复原图左侧透明角的遗漏：汉化标签四角都需要透明。构建将原图左侧遮罩镜像到右侧，每角3像素、共12像素透明；构建显式检查四个角alpha均为0。隐藏截片仍来自同一成品左8列，字形、边框及RGB像素不变。
