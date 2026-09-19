# 第九作：五月雨是铅灰的旋律

原文 `五月雨は鈍色の調べ`，证据为 `kibu9_Data/StreamingAssets/scratchpad` 内 `scratch1.dat` 成员 `title.gif`（240×240，带 `さみだれ`/`にびいろ`/`しらべ` 注音）与同图英文副题 `the requiem of rainfall sound`。与第八作的「仮面幻影殺人事件」无关。

安装目录相对于系列根目录为 `../../GmodeArchivesPlus_kibu9`。项目保持 `enabled=false` 作为公开发行门禁；本轮只做引擎核对与离线探针，未安装任何补丁，未操作游戏窗口。中文标题已由用户确认为“五月雨是铅灰的旋律”。

## 已核实的差异

- Unity Mono / Windows x64，Unity 2021.1.16f1（第八作为 2019.4.9f1），可使用公共 BepInEx 5.4.23.5 构建层。
- 对照已校验的第八作程序集（`441a790f…`）与第九作（`160a7873…`），CanvasEx 公共方法 45 个未变、56 个变化，第八作独有 133 个，第九作新增 27 个。原始 SJIS Unicode 表一致，不能据此推断 VM 一致。
- 第九作带 `CanvasEx.LoadScenarioEx`，没有 `RISUTO`/`RISUTO_MAIN`/`RISUTO_SUB`/`PaintList`/`INFO`/`SIORI`/`ROORU`/`SUKUROORU`。场景内新增 `AME`、`AME_SETTI`、`BUNSYOU_PERIOD`、`BUNSYOU_COLON`、`BUNSYOU_SEMI_COLON`、`BUNSYOU_SLASH`、`BUNSYOU_IRO`、`BUNSYOU_RUBI`、`BUNSYOU_F7`、`BUNSYOU_SPEED`。
- 场景容器与前两套都不同：没有 `FFFF` 信封、没有 16 位长度、没有逐场景 ZIP/JAR。scratch 成员原名即 `.bin`，载荷直接以 `20050117` 开头。`scratch3_*.dat` 那种分卷结构在这里不存在。
- 正文模型不同：`BUNSYOU` 读三个设置字节加一条 NUL 结尾字符串，由 `BUNSYOU_IRO`/`BUNSYOU_SPEED`/`BUNSYOU_RUBI`/`BUNSYOU_FADE` 和标点终止指令改变 `BunsyouStock` 逐字记录的颜色、速度、透明度与注音；没有 20050817 的逐行颜色/注音/控制平面。
- `KOMANDO`/`CHOUBUN_KOMANDO` 只读一个 16 位返回目标；`HAIKEI_SETTI` 为「1 字节标志 + 可选字符串」；`KYARA_SETTI` 为「字符串 + 两个 16 位值」；`FURASSYU` 为「1 字节 + 16 位」。不能照搬第八作的参数布局。
- 指令框架的重叠很大：第八作 50 个、第九作 48 个指令中，38 个编号与名称一致，其中 36 个操作数布局完全相同；真正不同的同名指令只有 `5 KOMANDO`、`40 HAIKEI_SETTI`、`255 BUNSYOU`。但容器、正文模型与运行时挂钩不同，所以仍是独立 adapter，只是把公共框架抽成 `engine/adapters/gmode-v2`（字节游标、SJIS 解码、标签表、指令循环、scratch 成员表），两个 adapter 各自只留差异；`gmode-20050117/vm.py` 从 182 行降到 118 行。

因此新增 `engine/adapters/gmode-20050117/`，实现容器读取与完整离线指令解析，并抽出公共框架 `engine/adapters/gmode-v2/`。未复制 `gmode-v1` 或 `gmode-20050817` 的运行时挂钩，也没有声称中文布局已经兼容。

该公共目录随后由另一轮工作扩展为完整公共适配层：除本作的 Python 脚本框架外，还收纳了从 `gmode-20050817/src` 与已删除的 `engine/unity-ui` 迁出的共用 C# 运行时与 UI 实现（`src/`、`ui/`），并新增正文断行、字宽几何、菜单记忆、分页记忆、历史显示等公共模块。因此本作后续运行时实现必须接入该公共层，不得从第八作复制实现；两作共用的部分见 `engine/adapters/gmode-v2/README.md`。

## 原文分布

`kibu9_Data/StreamingAssets/scratchpad` 的 TextAsset `scratch1.dat` 同时存放场景与人物/背景图：共 143 个成员，其中 122 个 `.gif`/`.jpg` 图片、9 个场景 `c1_01`..`c5_01`、外加 `define.bin`、`scn0.bin`、`start.bin`。开篇三个场景 `c0_00`/`c0_01`/`c1_00` 作为 TextAsset 单独放在 `kibu9_Data/StreamingAssets/file`，与 `title.mld` 同包。两处的偏移表格式一致。

`scn0.bin` 使用 `20050524` 标记、共 11 字节，不含标签表与正文区，单独校验，不计入场景数。

## 可复现操作

从系列目录运行 `run.ps1 extract --game kibu9`、`run.ps1 status --game kibu9`、`run.ps1 probe --game kibu9`。extract 校验原文件指纹、重建本机原文快照与研究文件，重复运行保留已有 cache 和 manifest；probe 使用公共 `engine/bepinex/build.py` 编译公共核心组件与独立 bootstrap 插件，核对插件身份、进程限制和组包。probe 不含译文与运行时挂钩，不是汉化补丁，也不安装到游戏目录。

适配器用例：`.venv/Scripts/python.exe -m unittest discover -s engine/adapters/gmode-20050117 -p "test_*.py"`（11 项），公共层 `.venv/Scripts/python.exe -m unittest discover -s engine/adapters/gmode-v2 -p "test_*.py"`（现 20 项，含本轮之后加入的公共运行时用例）。抽取脚本框架时对第八作与第九作做了前后指纹比对：5 个容器成员表 + 59 个脚本解析结果 + 1 个成员表 + 15 个脚本解析结果共 80 项，79 项逐字节一致；唯一差异是损坏容器的报错措辞（异常类型不变，仓库内无调用方依赖）。修改 gmode-v2 后须重跑两个 adapter 的用例。

机器报告位于本作 `research/engine-comparison.json`、`research/container-inventory.json`、`reports/extraction.json` 和 `reports/bootstrap_latest.json`；报告及原资源仅留本机；本文件记录可纳入 Git 的结论。

## 本轮完成情况

- 14 个场景镜像（12 个剧情文件 + `define.bin` + `start.bin`）全部逐字节遍历，标签表项全部落在合法指令边界，无未知指令、无未终结字符串；`scn0.bin` 单独校验。
- 指令编号取自 `CanvasEx::Game_adv` 的两个 `switch` 表，操作数布局取自各处理方法的读取调用序列，全部来自本作原程序集，不沿用第八作推测。
- 素材快照共 146 个成员、405,957 字节：`scratchpad` 的 `scratch1.dat` 143 个（12 个 `.bin` + 122 个 `.gif` + 9 个 `.jpg`），`file` 包 3 个场景。清单见 `research/material-inventory.json`。界面文案表 `StreamingAssets/localization` 的 `Localization`（1206 字节，`ja`/`en` 两列）已纳入原文快照；15 个出厂 key 与硬编码软键均已翻译并通过校验。
- 公共 BepInEx 构建层已复用：探针包 `out/bootstrap_*/Kibu9_Bootstrap_NOT_TRANSLATION.zip` 通过框架哈希校验、Cecil 插件身份校验和组包校验（25 个文件）。
- 未修改前作译文；本轮只写入 `games/09-samidare/`、`engine/adapters/gmode-20050117/`、`series.json` 与根 `README.md`。

## 抽公共框架后的回归记录

抽出 `gmode-v2` 改动了第八作适配器的共享代码，因此做了完整回归：

- 用例：`gmode-v2` 18 项、`gmode-20050817` 19 项、`gmode-20050117` 11 项，全部通过。
- 前后指纹：第八作 5 个容器成员表 + 59 个脚本解析结果，第九作 1 个成员表 + 15 个脚本解析结果，共 80 项，79 项逐字节一致；唯一差异是损坏容器的报错措辞，异常类型不变。
- 第八作端到端：`test_command_icons.py` 经 `scratch_resources` 取图并复核 10 个按钮、20 种状态的像素哈希，通过。
- 第八作完整构建：本任务在受限进程环境下运行到原生 Mono 绑定探针（`bepinex/tests/Run-MonoBindingProbe.py`）时中止，此前 Python 与 Cecil 各阶段全部通过（适配器 19 项、译文审计 16636/16636、待译 0、界面字典生成、插件编译、58 项真实程序集绑定校验 PASS）。该中止只与运行进程的沙箱环境有关：一个仅加载本机 `mono-2.0-bdwgc.dll` 并调用 `mono_jit_init_version` 的最小脚本即复现同样的断言，进度日志显示中止发生在 `mono_jit_init_version` 内部，尚未执行任何仓库代码。
- 第八作内容未变动：对 `games/08-kibu8` 的 258 个受控文件做了构建前后哈希比对，0 处变化；中止的构建只写了 `bepinex/build/` 下的可重建中间产物，没有产生新的 `out/` 发布包。

公共层随后由另一轮工作扩展，并把第八作完整构建在非受限环境下跑通到 0.5.60：`reports/gmode-v2-build.log` 记录全部运行时、菜单、历史与图片回归通过，`reports/gmode-v2-artifact-comparison.json` 记录 39 个发布产物与抽取前逐字节一致。本任务的解析层改动因此可判定为对第八作等价；受限环境下无法跑完的那一步不是代码回归。

## 运行时

正文接缝是 `CanvasEx::BunsyouStock(string)`，不是绘制层。一条显示行由若干 `BUNSYOU` 片段组成，行首片段携带该行字数；运行时用整行译文替换行首片段、把后续片段置空，并把 `Bun_nagasa[dan]` 更新为整行译文长度。逐字显示、颜色、速度、透明度、脚本字节与存档地址均未改动。字形绘制复用 `gmode-v2` 的 `BitmapFontAtlas` 与 `LegacyFontRenderer`：`StGraphics::DrawCharImpl(char[],int,int)` 的 IL 在两作完全一致。

说话人姓名与菜单项不走这条路径：`NAMAE_SETTEI` 的第一条 `StringRead` 是姓名牌（后两条是音效名与图像名），`SENTAKUSI` 的唯一 `StringRead` 是选项文字；运行时按指令前缀设置上下文、在 `StringRead` postfix 只替换第一条。界面文案走游戏自己的 `Steezy.Localize.Localization::Get(string)`（postfix 按 key 返回中文），硬编码的软键标签 `戻る` 在静态 `CanvasEx::command` 数组里原地替换，音效测试标签不译。

三个设置字节的含义已用全语料核实：第 1 字节 `BunsyouNagasaMax`（每行字数预算）、第 2 字节 `DanNoKazu`、第 3 字节**本行字数**。**7298 行的第 3 字节与拼接行文本长度全部一致**，这是行分组正确性的独立证据，也是译文行长预算的来源。姓名牌 34 处、菜单项 174 处，上限分别取语料中最长的 7 字与 11 字。

离线验证（均不上机、不启动游戏）：

- 编译期绑定：插件身份、进程限制、Harmony 挂钩签名与 **60 项反射绑定**（`CanvasEx` 字段与方法、正文与选项绘制入口、`StGraphics::DrawCharImpl`/`DrawString`、`drawOrigin`、四个行终止指令、`StringRead`、`command` 静态数组、`Localization::Get`）对真实程序集校验通过。
- 行为回归 `bepinex/tests/Run-RuntimeTests.ps1`：用真实译文包和真实 `BunsyouStock` 语义驱动生产挂钩，覆盖整行替换、多片段行续片段置空、预算收缩、未译行原样透传、续片段计数不泄漏、连续行独立 `Bun_nagasa`、重载复位、未知脚本不动、脚本名规范化、菜单项替换与未译项透传、姓名牌只替换三条字符串中的第一条且上下文用尽后失效、跨脚本不误替换、本地化 key 命中与未命中、软键标签、注音、分色、短译文推进、底部留白、英数字宽、稳定居中、右对齐与混排选项共 22 组断言。
- 译文包构建：正文超预算、姓名牌/菜单项超上限、脚本/偏移不存在、草稿与原文不一致、重复条目、缺 UI 均拒绝构建。
- 中文字库：KBF2 打包逻辑已上提 `engine/fonts/kbf2_atlas.py`，与第八作内联实现**逐字节一致**（同一 3479 字集，index 与 PNG 哈希相同）。

离线冒烟包 `out/smoke_*/Kibu9_SMOKE_NOT_RELEASE.zip` 由 `scripts/build_bepinex.py --smoke` 生成，只含小型固定文本样本，用于验证链路，**不是发行版**。完整草案现在可由 `scripts/build_bepinex.py` 生成 `Kibu9_CHS_0.1.14.zip`；正式入口会先拒绝缺译、超预算、视觉宽度超过 240px、UI 缺项和图片源漂移。

## 历史记录

第二个插件 `KibukawaHistory.dll`（系列标准路径 `BepInEx/plugins/KibukawaHistory/`）复用公共 `HistoryView`/`HistoryBuffer`/`ColoredHistoryLayout`/`HistoryState`/`HistoryAudioMute`，本作只补版本语义。

- **暂停**：本作没有顶层协程。`CanvasEx::Run` 是「`result = Game(); yield return WaitForFixedUpdate();` 直到 result 为假」，所以打开历史时用前缀跳过 `Game()` 并让 `__result = true`：协程继续存活，脚本推进与输入读取停止，画面停在最后一帧。不需要包裹协程，也不依赖 `Time.timeScale`（本作计时用真实时钟，缩放无效）。
- **采集**：在 `DrawAdvString(graphics, keta, dan, x, y)` 处按字采集，字段含义由 IL 确定（`Bun_moji[dan].Substring(keta,1)`，颜色 `Bun_iro[dan][keta]` 经 `ColorTable` 映射）。只记录已显示的字，不提前泄露未读文本；渲染器每帧重绘，故按原始 `(dan, keta)` 去重。
- **分块**：一条 `BUNSYOU` 是一行；一段发言是到下一个清空字符缓冲的指令（`BUNSYOU_PERIOD`/`BUNSYOU_ASTARISK`）为止的若干行，`BUNSYOU_SLASH`/`BUNSYOU_SEMI_COLON` 只在发言内换行。姓名每段发言出现一次。

离线验证：编译期 **23 项绑定**（`Game` 的 bool 返回、`BUNSYOU`、`DrawAdvString` 五参、`KeyFlush`、两个发言终止指令、两个 `LoadScenario`、以及 9 个字段）对真实程序集校验；行为回归 `bepinex/tests/Run-HistoryTests.ps1` 覆盖每段发言一条记录、姓名只出现一次、发言内换行、逐字重绘去重、颜色取自调色板与 `Bun_iro`、未显示的字不入历史、以及暂停前缀的返回语义。

## 图片本地化

全量目视核查 `scratch1.dat` 的 131 张 GIF/JPG 及 Unity 外壳纹理后，需要翻译的玩家可见图片为游戏内标题、两张标题菜单选中态和外壳封面。`rubi.gif` 是日文注音字形表，译文行由运行时关闭注音；`scratch1.dat/title.gif` 是旧副本，实际 `Game_title` 通过 `resource:///title.gif` 读取 `resources.assets` 的 `title` 纹理。

`images/generate_images.py` 从已校验的 `title`（240×240）和 `titleimage`（354×354）原生像素确定性生成中文图，字体由 `images/font-lock.json` 锁定；主标题固定为“五月雨是铅灰的旋律”，菜单为“从头开始”“继续游戏”。背景、英文副题与版权行保留。两张选中态维持原生 87×19 与透明度。

运行时复用 `gmode-v2` 的 `NamedImageRuntime`、公共 `ReplacementManifest` 和 `TextureReplacement`。两个菜单仍由 `CanvasEx.LoadGraphic(string)` 按原名替换；标题因原生代码绕过 `LoadGraphic`，在 `Game_title()` 后只替换静态 `Image_Haikei`；外壳只替换名为 `GameScreenShot` 且源纹理为 354×354 `titleimage` 的绑定。公共命名图片层现在允许全为 `*` 的路由在没有 `AppliArchive.AppliIndex` 的单篇作品运行，带章节选择器的旧作仍强制要求该属性。

离线验证：图片构建器核对 `resources.assets`、`resources.assets.resS`、`globalgamemanagers.assets`、`scratchpad` 和各图片的尺寸/像素哈希；Cecil 对真实程序集确认插件身份、`LoadGraphic`、`Game_title`、标题字段、`resource:///title.gif` 及两项菜单原生坐标；公共纹理测试 27 项覆盖方向、透明度、所有权、缓存与失败回退。完整冒烟包已包含图片插件，未操作游戏窗口。

## 菜单记忆

`CanvasEx` 自带 100 项选项记忆表，但记录与恢复都被 `if (komando_modori != -1) 跳过` 挡住，**带返回目标的文字菜单永远不记忆光标**。首个守卫在 `Game_command`+64（记录），另两处在 `Game_adv`+614/+679（恢复）。`src/NativeChoiceMemory.cs` 只重写这一个守卫读取与循环内两处 `Pos` 标识读取，记忆表、返回目标、取消分支逐字节保留；存储复用公共 `MenuMemory`。

本作 `Game_adv`/`Game_command` 是普通方法，所以直接对方法做 transpiler；本作没有取消路径上的页记忆。**分页记忆不适用**：`Page`/`MaxPage` 只在 `StaticInitializer` 里被引用，无任何方法读取，也没有列表界面。

离线验证：Cecil 直接按指令流核对 transpiler 期望的形状——`Game_adv` 2 个守卫 / 2 处标识读取，`Game_command` 1 个守卫 / 2 处标识读取，且每个守卫后都跟着原生记忆表；适配器用例另以 IL JSON 固化同样的期望。transpiler 自身在运行时再断言一次，对不上就抛错，而 `InstallChoiceMemory` 单独捕获异常，只停用记忆、保留正文翻译。

## 注音行与排版范围

`BUNSYOU_RUBI` 的 `rubi_info_kazu[i]` = `CreateRubiTexture` 返回值 − 调用前的 `RubiCreateCounter`。汉化版全局不画日语读音，所以运行时在 `CreateRubiTexture` 前缀原样返回传入计数：`kazu` 归零、不分配纹理、原生绘制循环无事可做；脚本注音元数据不变。该规则不依赖脚本偏移或译文包命中情况。

**正文仍不重排**：脚本已切好每行，`BunsyouNagasaMax` 与行尾字数在 7298 行上全部自洽。0.1.4 在绘制层接入第八作的字宽规则，不改文本缓冲、脚本命令或存档偏移：英文和数字（含全角占位符）显示为半角字形并前进 9px，中文前进 17px，汉字与英文/数字的交界增加 9px 空隙。居中模式按固定的 `BunsyouNagasaMax × 17px` 保持整块起点稳定，右对齐按当前行视觉宽度计算。0.1.8 补入第八作使用的 12px UI 点阵字库：正文和姓名牌继续使用 16px，选项及其他原生小型 UI 使用 13/7px 字距与 6px 汉字／英数间隔。构建会拒绝视觉宽度超过 240px 或超过固定居中块的正文，并拒绝超过 240px 的选项；当前全量正文最宽 187px、选项最宽 136px。

## 源文提取

`run.ps1 extract --game kibu9` 除场景与素材快照外，现在生成可翻译的源文提取稿：

- `work/dialogue-tagged.json`：**7506 条**（7298 正文行 + 174 菜单项 + 34 姓名牌），每条含 `script`/`kind`/`offset`/`source`/`target`/`limit`/`fragments`；`text_extraction_complete: true`。
- `texts/<脚本>.txt`：按偏移排序的可读对照（本机阅读，不进 Git）。
- 覆盖性已验证：`shipped_index` 列出的 7506 个文本单元与提取稿**一一对应**（集合相等），且每条 `source` 与出厂脚本**逐字节一致**、偏移唯一可解析、预算合法。
- 重新提取按 `(script, offset)` **保留已有译文**，只刷新源文——已用注入后重跑验证。
- 提取与校验彼此独立：`validate_units` 不依赖译文状态，所以源文稿一生成就能整体校验；`build(complete=True)` 要求覆盖**全部出厂文本单元**，而不只是草案列出的条目。

## 翻译与构建状态

正文、选项和姓名牌共 7506/7506 条已翻译，并按脚本分批进行源译对照与独立复核；字符预算、偏移、强调色分段和出厂覆盖均通过严格校验。界面 15 个本地化 key、硬编码“返回”软键、标题画面、外壳封面及两张标题菜单图片均已接入完整构建。

正式包 `Kibu9_CHS_0.1.1.zip` 在 0.1.0 的完整剧情与图片基础上补齐第八作已有的 Unity 外壳显示层：首页 `TitleDataModel`、序列化标签、程序集硬编码 UI、官方本地化 key 和中文系统字体均由内存钩子处理，不改写原版 assets。适配器、正文替换、UI 行为、历史记录、图片方向与透明度、真实程序集绑定均通过；包内 42 个文件已安装并逐一比对一致，仍需实机确认显示与输入。

0.1.2 补齐 `HowToPlayDialog` 的四页玩法说明。原作把页内文字烘焙在四张 930×632 Sprite 中，普通 UI 文本钩子无法触及；构建现按本作七行控制表和复刻说明重新排版四张中文页，并在 `ChangePage(int)` 后只替换 `guideImage.sprite`，保留原生翻页、箭头和关闭逻辑。构建同时校验源 bundle 哈希、`HowToPlayDataModel` 页序、Sprite 名称、纹理尺寸和所有中文文字边界。

0.1.3 修复正文首个短译文 `c0_00:172` 后无法推进且文字音效循环。原生 `BUNSYOU` 在进入 `BunsyouStock` 前按日文参数长度增加 `SyoriMojiCount`；此前只同步了中文缓冲区、字符平面与 `Bun_nagasa`，9 字原文替换为 7 字译文后计数永久残留 2。运行时现对每个替换片段同步源译长度差，包含置空的续片段和分色片段。离线桩也改为按真实 IL 顺序计数，并加入该开场行完整揭示后必须进入终止状态的回归用例。全量 7298 条正文中有 6315 条短译文，因此这是系统性修复。

0.1.4 把剧情点阵字形整体上移 3px，使最底一行墨迹下方固定留下 3 个物理像素；该作用域只包住 `DrawAdvString`，首页和其他 UI 坐标不变。同时按第八作实现英文、数字、汉字交界与选择肢的字宽规则，并保留第九作选择肢原有的轮廓、基线和颜色层。离线测试覆盖左/中/右对齐、全角字母数字映射、连续英文数字、汉字交界、残留行隔离、选择肢和作用域外 UI 坐标。

0.1.5 修正第九作历史记录的两个实机问题。历史分段现在绑定到原生 `ClearBunBuffer()` 的一次性清屏点，不再把会跨帧反复执行的 `BUNSYOU_PERIOD` / `BUNSYOU_ASTARISK` 当作段落结束，因此句末逐字播放时不会把每个字拆成一条记录或重复姓名。历史入口也接入 `StDisplay` 的原生左软键事件 21：手柄 L 肩键及游戏配置中的键盘 Q/L 共用该路径；只有左软键空闲时显示并接管“历史记录”，原生“返回”等操作仍保持原意。

0.1.6 修正第九作历史记录按首次绘制时序追加所造成的字符错序。此 VM 会先绘制少量字符，再在 `Resumed/SystemResumed` 状态全量重画；开场三片段地点行因此可能按 `row3:k0,k5 → row0 → row1 → row3:k1..k4` 到达钩子，旧实现会得到“鞠台……滨市鞠滨”。第九作采集器现在只缓存实际绘制过的字符，并在每次新增字符后按 `(row, keta)` 重建当前记录，因此结果稳定为日期、天气、空行和完整“鞠滨市鞠滨台”。

0.1.7 修正历史正文颜色被统一显示为白色。第九作的 `BunsyouStock` 已把 `NowMojiColor` 的最终 24 位 RGB 直接写入 `Bun_iro[row][keta]`，旧历史适配器却把该值再次当作 `ColorTable` 索引，绝大多数颜色因此越界并回退为白色。正文现直接保留 `Bun_iro` RGB；姓名牌的 `Namae_color` 确实仍是调色板索引，其原有取色路径不变。回归覆盖一行译文两段不同 RGB 的强调色。

0.1.8 按第八作补入独立 12px 小型 UI 点阵字库，正文与姓名牌仍保持 16px。所有选项均改用 Unicode 视觉宽度计算，纯中文选择肢不再经过遇到简体字便截断的 CP932 `Strlen` 路径。姓名牌保存前临时还原为日文，原生 `SaveData` 完成或异常退出后恢复中文，读档后再按完整日文原文翻译。`Ds_sub`／`Ds_sub2` 的整句状态文案也在原生测量和逐字拆分前翻译，覆盖旧联网服务界面。

0.1.9 移除对旧截断姓名前缀的运行时猜测。用户当前的 0.1.7 时代 `save/SaveData` 已按原生格式直接修复：重建 20 个姓名／头像字符串对、把姓名恢复成完整 CP932 日文源值、重算大端 payload 长度并保持 65536 字节容器及后续字段不变。修复前文件已单独备份；新存档继续由保存前日文还原机制保护。

0.1.10 修正分色正文中的日语注音残留。`BUNSYOU_RUBI` 不只会出现在一行正文之前，也会出现在开头片段和后续强调色片段之间；此时 `Pos` 指向后续 `BUNSYOU`，不再等于整行翻译包的起始偏移。运行时现先检查当前 `LineState` 是否已确认该整行被翻译，只在新行尚未开始时才按即将执行的 `BUNSYOU` 偏移查询。回归覆盖截图对应的 `c0_00:3087`：第一段“哇啊”入库后，位于 3100 的“いづな”注音必须归零，不生成纹理。

0.1.11 按汉化版显示规则全局关闭日语注音。`CreateRubiTexture` 前缀不再依赖脚本偏移、译文包命中或当前行状态，插件就绪后所有 `BUNSYOU_RUBI` 都原样返回当前 `RubiCreateCounter`，使注音格数恒为零。回归同时覆盖截图中的行中注音与译文包不存在的未知偏移。

0.1.12 重译序节 `c0_00:3420-3607` 的整轮对白。结合前文，`それはいい！` 是生王打住话题，并非称赞“说得好”；后续按伊纲冷淡吐槽、生王尴尬嘴硬后当场服软的语气重写为“这个先不提！／……你这是干嘛？／在学老师说话？／一点儿也不像。／我不是都说了嘛，／这事就算了！／好啦，对不起嘛！／………？／算了，还是说正事吧。”，所有行仍在原始显示上限内。

0.1.13 将角色口头禅 `それはいい` 锁定为“这个先不提”，并统一全作 6 处原句及带 `ええい`、`まあ` 的变体。`それは良かったですね` 等“结果很好”的普通句型不属于该术语。

## 并发改动说明

首次 extract 时，前作文件比对报告 `games/08-kibu8/reports/installation_latest.json` 被其他会话改写（该记录已是 0.5.59，晚于 `games/08-kibu8/COMPATIBILITY.md` 记录的 0.5.1），`games/08-kibu8/work/cache.json` 与 `dialogue-tagged.json` 同期也由外部改写。重跑后比对为一致。这些文件属第八作且已被 Git 忽略；本任务没有读写它们，也不据此回退任何内容。

## 0.1.14 开场指代修正

开场 c0_00:4732-4756 的发言人是伊纲，原文是在接少年的评价、把生王称作怪大叔。译文由误指伊纲自己的“那我就当个怪大叔吧”修正为“那就叫你怪大叔好了”。

## 2026-09-19 中文自然换行（0.1.21）

普通 SLASH 对话行使用预计算中文布局；保留点击边界、空行、特殊对齐、逐字状态和颜色。布局文件 dialogue-layout.bin 必须与 translations.bin 一同构建、发布。详见 out/reflow_20260919/REPORT.md；离线检查通过，未做全篇实机验收。

## 2026-09-20 全篇校对完成（0.1.22）

完成全篇实机通关校对，统一上下文翻译、强调色范围、中文自然断行、省略号和破折号标点，并补充伊纲（Izuna）、伊兹米（Izumi）及泉（Izumi）的读音梗。7506 条文本、7298 条正文颜色结构、中文布局、运行时替换、历史记录、图片与字体构建均通过离线回归，项目进入可发布状态。
