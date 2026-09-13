# 第八作：假面幻影杀人事件（暂译）

原文 `仮面幻影殺人事件`，证据为 `scratch3_1.dat/c0-01.bin` 中字间留白的标题。不是第一作的“假面幻想”。

安装目录相对于系列根目录为 `../../GmodeArchivesPlus_kibu8`。项目保持 `enabled=false` 作为公开发行门禁；0.2.0 测试补丁已通过本作显式安装入口安装，未操作游戏窗口，实机验证由用户进行。

## 已核实的差异

- Unity Mono / Windows x64，可使用公共 BepInEx 5.4.23.5 构建层。
- 对照已校验的第六作程序集，统一命名空间和协程编号后，CanvasEx 方法仅 6 个相同、5 个变化，旧方法缺失 45 个，新方法 223 个。SJIS Unicode 表一致，不能据此推断 VM 一致。
- 旧 `Read`、`ExeText` 和 `Script` 协程缺失；新入口包括 `LoadScenario`、`StringRead`、`ShortRead` 和 `Game` 协程。StringRead 有 100 字节局部缓冲限制。
- `scratch3_1.dat`、`scratch3_2.dat`、`scratch3_3.dat` 含 13、27、19 个 JAR，共 59 个。每包一个同名 BIN；同名 start/define 等在分卷间独立保存。
- BIN 有 `FFFF` 信封、16 位小端长度、`20050817` 标识、标签表及正文指令区；不同于前作的 scn/define 参数表。ShortRead 的指令参数顺序另为大端，不可把信封字节序用于全部指令。

因此新增 `engine/adapters/gmode-20050817/container.py` 与 `vm.py`，分别实现容器读取与完整离线指令解析。未复制 gmode-v1 的运行时挂钩，也没有声称中文布局已经兼容。

## 可复现操作

从系列目录运行 `run.ps1 extract --game kibu8`、`run.ps1 status --game kibu8`、`run.ps1 probe --game kibu8`。extract 校验原文件指纹，重复运行保留已有 cache 和 manifest；probe 使用公共 `engine/bepinex/build.py` 编译核心组件及独立 bootstrap 插件，核对插件身份、进程限制和组包。probe 不含译文与运行时挂钩，不是汉化补丁。

机器报告位于本作 `research/engine-comparison.json`、`research/container-inventory.json`、`reports/extraction.json` 和 `reports/bootstrap_latest.json`。报告及原资源仅留本机；本文件记录可纳入 Git 的结论。

## 本轮翻译完成情况

- 59 个 BIN 的 41,337 条指令完整遍历，正文 1,848,077 字节全部覆盖，3,242 个标签均落在合法指令边界；8 项容器/VM 测试通过。
- 正式稿为 `work/dialogue-tagged.json`：16,636 条剧情与脚本菜单，原文约 326,954 字；22 批均已翻译并交叉审校，另记录 109 项审校决定及 180 处统稿调整（含重复公共场景统一）。这仍是初译审校稿，并非发布级语义保证。
- `work/ui-localization.zh-CN.json`、`work/ui-assembly.zh-CN.json`、`work/ui-serialized.zh-CN.json` 共 149 处可见界面文本已译；64 处技术哨兵、模板及调试文本单独排除。序列化文本使用资源、对象与解压后字段位置定位，禁止当作压缩包直接字节替换地址。
- `work/cache.json`、`work/manifest.json` 已同步；控制标记序列全量匹配，无待译项，无未处理的假名或私用区字符候选。颜文字仅按源文中的精确形式放行。
- `work/review-summary.json` 记录独立审阅范围、最终批次摘要及验证统计。21 个前作译文/术语文件与翻译开始前一致，178 个原游戏文件哈希一致。

## 复现译稿检查

在系列目录使用 `.venv/Scripts/python.exe games/08-kibu8/scripts/translation.py collect --complete` 汇总批次与界面；使用 `check --complete` 只检查正式稿。`python -m unittest discover -s engine/adapters/gmode-20050817 -p test_*.py` 验证解析器。`run.ps1 status --game kibu8` 校验源文件并显示当前阶段。

## 运行时测试补丁 0.2.0

已接入原读取器后置的 Unicode 显示缓冲替换：BUNSYOU、ROLL、SCROLL 保留原物理行和控制事件。StringRead 只替换菜单/提示参数；姓名牌和书签在最终绘制处翻译。INFO 在绘制协程单次 MoveNext 期间临时替换，finally 恢复。Script、Pos、LabelIndex、原始姓名和书签持久化字段不变；无需修改 SJIS 编码器或重定位存档。

保留原色表、渐变和控制事件。中文单槽显示使用 ASCII 全角等价字形，过长行按原对齐方式同步调整字距与字宽。原日语 ruby 在中文行不绘制，1910 组原始元数据保留在原脚本和研究材料中。8 处行内译注从原单行缓冲移至可收起的备注栏，在对应行显示完时出现。

公共 `engine/bepinex/build.py` 负责依赖验证、编译和组包；公共 BitmapFontAtlas/LegacyFontRenderer 源码直接复用，并补偿本作 drawOrigin。字库构建复用 `engine/tools/pixel_font.py`，覆盖3445字形、无缺字。13 项容器/VM/编译包测试、51 项实际程序集绑定及纯 CLR 显示缓冲集成检查通过。测试不会启动游戏或加载 Unity 窗口。

测试补丁构建：在系列根目录执行 `.venv/Scripts/python.exe games/08-kibu8/scripts/build_bepinex.py`。安装预检/安装：相同 Python 执行 `games/08-kibu8/scripts/install_patch.py --dry-run` 或 `--install`。安装按最终构建报告列出的文件逐一校验、备份已有文件、写入并核对哈希；失败回滚。恢复命令是 `--restore installations/具体记录/installation.json`（传入该文件绝对路径）。

`reports/build_latest.json` 和 `reports/installation_latest.json` 记录最终包与安装状态。系列 enabled=false 暂保留为公开发行门禁，不将本次离线验证冒充实机验收。测试补丁使用本作上述显式入口。

## 待完成

用户实机检查中文布局、菜单、存读档、滚动字幕、译注、标题及历史记录可读性。游戏程序集和原始资源保持原样，未操作游戏窗口。

本次安装已核对36个补丁文件，178个原始游戏文件哈希保持一致；此前无同名文件，因此无需备份旧文件。安装清单完整记录新增文件，恢复脚本可按清单移除。

## 完整补丁 0.3.0

在正文补丁基础上纳入图片替换插件 1.2.0 与本作历史记录入口 1.6.2。图片包含三篇标题、三项菜单高亮和外壳封面；并非所有游戏图片文字均已汉化。资源按 AppliIndex 和真实资源树定位，公共 TextureReplacement/ReplacementManifest 复用不变。标题图生成及文件见 images/GENERATION.md。

历史复用公共 HistoryBuffer、ColoredHistoryLayout、RuntimePolicy，仅适配本作实际绘字及输入入口；只记录 DrawAdvString 已绘制字符，保留中文姓名与当时颜色，块内重绘去重，不提前读取后续对白。H/PageUp 开关，原生左软键空闲时也可打开。实际绑定、绘字披露、暂停和容量测试已离线通过。

完整构建仍使用公共 BepInEx 构建层，并强制检查 series.json 的 required_plugins；缺少图片或历史插件将停止组包。0.3.0 包共54个文件，最终安装版本及备份路径以 reports/installation_latest.json 为准，实机验收仍待用户完成。

## Native pixel fonts (0.3.3)

From the series root, run `.venv/Scripts/python.exe games/08-kibu8/scripts/fetch_pixel_font.py`, then `.venv/Scripts/python.exe games/08-kibu8/scripts/build_bepinex.py`. The downloader checks versioned official URLs, sizes and SHA256 values in the two font locks. Upstream binaries and generated atlases are ignored by Git. The patch archive includes the generated fonts and attribution. Seven supplemental glyphs are authored as reviewable text in bepinex/supplement-12.json.

## Translation container, current as of 0.4.1

The package uses the same schema-1 JSON fields and KBZH binary encoding as previous games, named translations.json and translations.bin, with the unchanged shared reader and data classes. Source and target contain plain text only. Script names are short canonical resource paths; a generated C# identity table maps verified original script hashes to these names once per script. Instruction identifies the original command offset and slot identifies a text segment across its rows (or -1 for StringRead arguments).

The adapter reads the original script to recover row boundaries, colors, control events and ruby layout. Translation segments follow the original color/control boundaries; tags exist only in the tagged editing/review draft. No tagged target parser or legacy container fallback is retained. UI/localization catalogs use the same pack. Original game files and previous games' translations are unchanged.

## Font scope correction (0.4.2)

## Dialogue spacing correction (0.4.3)

## Whole-string glyph geometry correction (0.4.4)

## Native width layout and INFO (0.4.5)

Horizontal glyph compression is removed. Standard dialogue wraps to at most 12 fullwidth native Unifont glyphs per row; text/color/control planes are sliced together without changes to event bytes or script offsets. Spaced titles reduce blank advances rather than glyph width. Reflowed dialogue updates ScrollDan and requests the original Resumed redraw after four visible rows, without advancing the VM or reveal cursor. Long translator notes remain in their separate panel.

INFO uses 17px nonblank advance and 8px separators, 16px glyphs positioned at top y=1. Its original 14px transition clip temporarily expands to 18px and is restored afterwards. All 291 INFO lines fit within 236px. Full-corpus tests validate native scale=1 and horizontal bounds for every visible dialogue character, preserve color/control arrays, and check viewport updates leave script/reveal positions unchanged. Visual and animation acceptance remains with the user.

## INFO font preference (0.4.6)

## Text-choice font preference (0.4.8)

## INFO vertical alignment (0.4.9)

## 0.4.10 文字子菜单光标记忆

实测日志确认横排图标菜单原生记忆正常。原脚本 scratch3_1.dat/i0-00 的呼叫子菜单 KOMANDO 返回目标为 0；原 Game_command 和 Game_adv 在 komando_modori != -1 时跳过原生记录与恢复。NativeChoiceMemory 仅替换记忆循环前的条件读取，让 NowCommand/NowChobunCommand 复用原 50 项记忆表，保留真正的返回目标与返回分支。未新增缓存或存档格式。

Run-ChoiceMemoryTests.ps1 执行原始 IL 的记录/恢复循环，复现旧行为，并对生产 transpiler 变换后的 IL 检查普通/长文字菜单、返回目标 0/23/-1、返回分支及非文字菜单不变。该功能记录最后确认的选项；仅移动光标后取消不写入，与原作一致。临时 CursorProbe 不进入正式包，安装本版时移除。实机效果待用户验证。

## 0.4.11 适配层归位

字体图集、字形绘制、正文排版、菜单记忆移至 engine/adapters/gmode-20050817/src。CanvasRuntime 提供引擎运行时基类与挂钩；本作 Plugin 继承它，保留身份、资源/字体加载、本作 UI 和注释面板。RuntimeLayout 从本作提供行宽、字距、INFO 基线和小字体页面范围。构建和回归直接引用适配层源码；作品目录无重复实现。保持 0.4.10 的字体、坐标、菜单记忆和译文行为。

## 0.4.12 居中字距取整

FitDraw 的逐字坐标使用 Math.Round 默认偶数取整，居中起点为半像素时，17px 步长会交替成为 16/18px。改为一致的中点取整策略，保持正文 16px、步长 17px，不更换字形或引入缩放。全场景回放新增相邻非空白字符固定步长断言，原实现出现 advance=18，修复后通过。

## 0.4.13 底部文本框行数

按用户确认，第八作底部显示区比前作少一行。RuntimeLayout 由本作指定 3 行总容量，有姓名栏时正文容量为 2 行；重排后超过容量时推动原生 ScrollDan 并请求重绘。修正原生重绘在滚动后跳过姓名行时丢失的纵向偏移，使逐字绘制和重绘使用同一基线。字号仍为 16px，不压缩文本。已新增姓名栏第三行前滚动、无姓名三行容量、滚动后基线的回归检查；实机待验证。

## 0.4.14 五行与姓名保留（替代 0.4.13 容量判断）

前作 FHeight=font.GetHeight()+1，16px 字体对应 17px 行距，普通五行、姓名占一行。按用户指定，本作采用 16px 字高+2px 间隔=18px 行距，总容量五行，有姓名时正文四行。底部首行从 Moji_y-32 开始，常态为 136/154/172/190/208，最后一行字高16，底部224。此策略由本作 RuntimeLayout 提供，适配层统一处理逐字绘制与重绘。滚动后补绘固定姓名，保持原姓名内容和颜色。保留原脚本与控制事件；当前视口滚动不等同于前作协程的额外点击等待机制，后者需单独适配本引擎。

## 0.4.15 正文布局作用域

## 0.4.16 底部菜单整体位置

用户确认问题是整列菜单太高。原 PaintCommand 按总选项数向上展开，6项时标题 y=128。普通底部菜单改为标题 y=136、选项起点150、14px行距，最多显示5项；通过选中项计算窗口，绘制仍调用原 DrawAdvCommand，不改变 SentakuStock、CommandCursorPos 或跳转编号。非底部菜单、图标菜单保留原绘制。回归检查6项选中最后一项时显示索引1..5、标题条y=135、末项y=206、状态不变及字库作用域恢复。

## 0.4.17 删除新增菜单滚动

按用户要求完整删除 0.4.16 的 BeforeBottomMenu、MenuWindowTop 及相应挂钩/窗口测试，恢复原 PaintCommand 按总选项数绘制全部选项及原始起点。没有保留开关或兼容实现。正文五行、姓名保留、原生选项记忆和菜单字体设置不属于此项删除范围。

## 0.4.18 仅恢复整列菜单位置

按用户澄清，保留正确的整列起点修改，仅移除菜单滚动。NativeMenuPosition 只替换原 PaintCommand 底部起点赋值，使首项 y=150、标题y=136；原有全部选项循环、编号、高亮与绘制指令完整保留。没有窗口、滚动或五项限制，第六项仍绘制在 y=220。原始 IL 回归逐条验证除起点赋值外的指令不变。

## 0.4.19 全屏文字排除五行滚动

BeforeDialogueViewport 仅在普通底部文字区（MojiHani_tate=0 且 Moji_y=168）应用五行预算。全屏顶部/居中模式以及翻转后文字区域不改 ScrollDan 或 Resumed；保留原版纵向布局。全场景回放新增全屏模式长文本检查，先复现旧实现错误滚动，再验证修复与底部五行逻辑均通过。

## 0.4.20 设置页左栏对齐

设置页原 DrawString 左栏起点统一 x=9，但四条翻译保留了原日文开头的全角/半角空格，导致可见文字起点不同。仅去除声音、背景音乐设置、音效设置、读取存档译文开头的排版空格，统一左对齐；不调整行高、字号、数值列或其它菜单坐标。

## 0.4.21 合并无语义停顿的旧换行

旧 PrepareDialogueRows 逐原行 Wrap，导致“深度”的“度”单独成行。改为一次对白块内先按与 gmode-v1 相同的语义原则合并，再按本作12列重排；原文和译文都以停顿标点结尾、末尾控制事件、空行、间隔标题、彩色姓名后引号及译注锚点保持边界。不同对白块不合并；不变更原脚本与控制事件。回归覆盖截图句子从三行变两行、颜色/终止控制保留，以及停顿、姓名边界。前作译文及运行时代码未改。


## 0.5.0 字库

12px 界面及指令图标统一使用固定提交的 Z Labs Pixel 12px M CN 原始 KBITX 字形。像素、字距、边界与基线保留；正文仍用 16px Unifont。指令图标每字12px，两个字占24px，原图标上部保持不变。下载脚本校验大小和 SHA256，源字库不进 Git 或发布包，完整 OFL 许可随包附带。

## 0.5.1 行动按钮恢复

按用户反馈，行动按钮图片恢复原先 10px Fusion Pixel 标签、每侧2px留白、原图案和两种状态。此依赖仅用于生成按钮图片；12px 动态界面继续使用 Z Labs，正文仍是16px Unifont。

## 0.5.68 制作人员名单排版

正文软换行合并现在也检查原文的全角空格；即使译文更短，原作刻意分行的制作人员名单也不会被拼成一行。中文版制作人员姓名恢复原名单的全角字距，职务、空行和每位人员各自保留原始行。

## 0.5.69 片尾标题字距

片尾再次显示“假面幻影杀人事件”时，使用与序章标题相同的全角字距，并保留“杀”的强调色。扫描所有同源排版文本后，这是唯一一处字距不一致。
