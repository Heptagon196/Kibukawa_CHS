# G-MODE 20050117 适配器

第九作原始 `CanvasEx.LoadScenario` 使用 `20050117` 场景格式，与 `gmode-v1` 的 `Read`/`ExeText`/`Script` 协程、以及第八作的 `20050817` 场景格式均不同。本目录提供该引擎的离线容器与指令解析，以及按本作方法签名接入 `gmode-v2` 公共层的运行时；运行时尚未经实机验证。

## 运行时

正文接缝是 `CanvasEx::BunsyouStock(string)`，不是绘制层：

- 本作一条显示行由若干 `BUNSYOU` 片段组成，`BUNSYOU` 读三个设置字节 + 一条字符串，`BunsyouStock` 把字符串追加进 `Bun_moji[dan]`，并按字填充 `Bun_iro`/`Bun_speed`/`Bun_alpha`/`Bun_jikan`；推进 `NowStockMojiDan` 的是 `BUNSYOU_SLASH`/`_SEMI_COLON`/`_PERIOD`/`_ASTARISK`。
- 三个设置字节的含义已用全语料核实：第 1 字节是 `BunsyouNagasaMax`（每行字数预算，非零时更新并保持），第 2 字节是 `DanNoKazu`，第 3 字节是**本行字数**（只在该行首片段非零）。7298 行的第 3 字节与拼接后的行文本长度**全部一致**，这是行分组正确性的独立证据。
- 因此运行时在行首片段用整行译文替换该片段、把后续片段置空，并把 `Bun_nagasa[dan]` 更新为整行译文的长度。逐字显示、颜色、速度、透明度、脚本字节与存档地址都不动。
- 字形绘制复用 `gmode-v2` 的 `BitmapFontAtlas` 与 `LegacyFontRenderer`：`StGraphics::DrawCharImpl(char[],int,int)` 的 IL 在两作完全一致，而 `RenderStart`/`RenderEnd` 不同，共享渲染器从活的 graphics 类型绑定，所以调用的是本作原方法。
- 键用「脚本名 + BUNSYOU 脚本相对偏移」，与系列既有译文包一致；`BunsyouStock` 阶段 `Pos` 已越过操作码，故偏移取 `Pos - 1`。
- **说话人姓名与菜单项**不走 `BunsyouStock`：`NAMAE_SETTEI` 的**第一条** `StringRead` 是姓名牌文字（随后还有音效名与图像名，必须区分），`SENTAKUSI` 的**唯一** `StringRead` 是选项文字。运行时在这两个指令的前缀设置上下文、在 `StringRead` 的 postfix 按索引替换，只改第一条。
- **界面文案**：Unity UI 走游戏自己的 `Steezy.Localize.Localization::Get(string)`，postfix 按 key 返回中文，保留预制体、语言切换与重新本地化路径；游戏硬编码在静态 `CanvasEx::command` 数组里的软键标签（`戻る`）在初始化时原地替换，音效测试用的 `♪ N` 不动。

目前已实现正文行、姓名牌、菜单项、界面文案、历史记录与菜单记忆；尚未实现图片替换。

## 注音行

`BUNSYOU_RUBI` 为后续基准行提供日语读音：它把 `rubi_info_start[i]` 记为当前 `RubiCreateCounter`，再用 `CreateRubiTexture` 的返回值更新计数，`rubi_info_kazu[i]` 即两者之差。译文行上再画假名会覆盖错误的位置，因此运行时在 `CreateRubiTexture` 前缀里**原样返回传入的计数**：`kazu` 变成 0，原生绘制循环没有可画内容，也不分配纹理；脚本里的注音元数据保持不变，**未翻译的行照常显示注音**。判定依据是 `Pos`——注音指令紧接其基准 `BUNSYOU`，纹理创建时操作数已读完，`Pos` 正好等于基准指令的偏移。

## 正文断行与字宽几何：本作不适用

这两项公共能力本作**刻意不接入**，理由是引擎本身不做重排：

- 脚本已经把每行切好。`BunsyouNagasaMax`（每行字数预算）与行尾第 3 字节（本行字数）在 **7298 行上全部自洽**，一个 `BUNSYOU` 就是一行，行的划分不是运行时决定的。
- 字形前进量由共享 `LegacyFontRenderer` 自己按原生字体度量，本作不需要单独的字宽策略。
- 因此译文若超出行长预算，构建期直接拒绝并报出脚本与偏移，而不是在运行时重排。

要放宽这一限制（允许更长的中文并自动重排）需要合并/拆分原生行，那超出了脚本能表达的结构。届时才需要接入 `gmode-v2` 的 `TextBreaks`/`TextGeometry`——第八作之所以用到它们，是因为它的正文按行平面存放、可以重写行结构。

早先版本里曾有一个只被赋值、从未被读取的 `RuntimeLayout`，已在本轮删除：本作没有需要它的排版策略。

## 菜单记忆

`CanvasEx` 自带一张 100 项选项记忆表（`Sentaku_kioku_id`/`_pos`/`_top_pos`），但记录与恢复两处都被 `if (komando_modori != -1) 跳过` 挡住：**有返回目标的文字菜单从不记忆光标位置**。`src/NativeChoiceMemory.cs` 只重写这一个守卫读取，以及循环内用于标识菜单的两处 `Pos` 读取，记忆表本身、返回目标与取消分支都不动。存储复用 `gmode-v2` 的 `MenuMemory`，键为脚本身份加菜单标识（可取消的文字菜单用其打开指令的偏移取负值）。

与第八作不同：本作 `Game_adv`/`Game_command` 是普通方法，没有协程，因此直接对方法本身做 transpiler（不需要 `EnumeratorMoveNext`）；本作也没有取消路径上的页记忆需要记录。transpiler 会断言守卫数量（`Game_adv` 2 个、`Game_command` 1 个）与标识读取数量（各 1/2 处），对不上就抛错。

**分页记忆不适用**：本作 `Page`/`MaxPage` 只在 `StaticInitializer` 里被引用，任何方法都不读，也没有 `RISUTO`/`PaintList` 之类的列表界面，因此不接入 `PageMemory`。

记忆安装是增强而非前置条件：`CanvasRuntime.InstallChoiceMemory` 单独捕获异常，transpiler 不匹配时只停用记忆并保留正文翻译。

## 历史记录

`src/HistoryRuntime.cs` 是 `KibukawaHistory.HistoryView` 的本作实现，复用公共 `HistoryBuffer`/`ColoredHistoryLayout`/`HistoryState`/`HistoryAudioMute`。

- **暂停**：本作没有顶层协程。`CanvasEx::Run` 是 `do { result = Game(); yield return new WaitForFixedUpdate(); } while (result)`，所以打开历史时用前缀跳过 `Game()` 并把 `__result` 置 true：协程继续存活，脚本推进与输入读取全部停止，画面停留在最后一帧。这比包裹协程更简单，也不需要 `Time.timeScale` 生效。
- **采集**：在真正绘制处取字。`DrawAdvString(graphics, keta, dan, x, y)` 每显示一个字调用一次，字段含义由 IL 确定（`Bun_moji[dan].Substring(keta,1)`，颜色取 `Bun_iro[dan][keta]` 经 `ColorTable` 映射）。因此历史只记录玩家已经看到的字，绝不会提前泄露未读文本。渲染器每帧重绘可见字符，故按原始 `(dan, keta)` 去重。
- **分块**：一条 `BUNSYOU` 是一行，一个"发言"是到下一个清空字符缓冲的指令（`BUNSYOU_PERIOD`/`BUNSYOU_ASTARISK`）为止的若干行；`BUNSYOU_SLASH`/`BUNSYOU_SEMI_COLON` 只在发言内部换行，不另起一条历史。这样姓名只在每段发言前出现一次。
- 姓名牌颜色取 `ColorTable[Namae_color[NowNamae]]`；姓名字串本身已是中文，由正文插件在 `NAMAE_SETTEI` 读入时替换。

## 行长与字宽约束

- 正文每行中文字数不得超过该行的 `BunsyouNagasaMax`（实测 2–11 字），构建期强制。
- 姓名牌上限 7 字、菜单项上限 11 字，取自语料中已发行的最长字符串——比它更长需要先做实机确认。三者都以字符计，因为原生渲染器每字前进一个步长。

## 与 gmode-20050817 的重叠与差异

指令框架的重叠很大，不能据此把两个版本当成同一个引擎；承载文字的那一层确实不同，因此仍是独立 adapter，但公共部分只写一次。

| 项目 | 结论 |
| --- | --- |
| 指令编号与名称 | 第八作 50 个、第九作 48 个，其中 **38 个编号与名称完全一致** |
| 操作数布局 | 这 38 个里 **36 个布局完全相同** |
| 真正不同的同名指令 | `5 KOMANDO`（第九作只读一个 16 位返回目标）、`40 HAIKEI_SETTI`（第九作无第二条字符串与两个短整数）、`255 BUNSYOU`（正文模型不同） |
| 第九作新增 | `AME`、`AME_SETTI`，以及 `BUNSYOU_PERIOD`/`_COLON`/`_SEMI_COLON`/`_SLASH`/`_IRO`/`_RUBI`/`_F7`/`_SPEED` 共 10 个 |
| 第八作独有 | `INFO`、`ROORU`、`SIORI`、`RISUTO`/`RISUTO_MAIN`/`RISUTO_SUB`、`SUKUROORU` 等 12 个 |
| 容器 | 不同：没有 `FFFF` 信封、没有 16 位长度、没有逐场景 ZIP；成员原名就是 `.bin`，载荷直接以版本串开头。成员数是 1 字节（第八作图片容器为 2 字节） |
| 正文模型 | **不同**：`BUNSYOU` 读三个设置字节加一条 NUL 结尾字符串，由 `BUNSYOU_IRO`/`_SPEED`/`_RUBI`/`_FADE` 及标点终止指令改变 `BunsyouStock` 逐字记录的状态；没有 20050817 的逐行颜色/注音/控制平面 |
| 运行时挂钩 | **不同**：第九作 `Game`/`Game_adv`/`Game_command` 是普通 `bool` 方法，第八作是 `<Game_adv>d__…` 协程，`CanvasRuntime` 那套挂钩无法复用 |

版本中立的框架已抽到 `engine/adapters/gmode-v2`：本目录的 `vm.py` 只保留指令表、三个条件操作数和裸信封，`container.py` 只保留 1 字节成员数与场景筛选。

## 职责

- `container.py`：读取 scratch 容器的成员表；成员名、偏移、长度与载荷边界由 gmode-v2 校验。
- `vm.py`：`20050117` 指令表与操作数布局，标签必须落在合法指令边界；`parse_index` 单独校验 `scn0.bin`。

两者都是离线解析器，不修改脚本字节、存档地址或运行时状态。

## 表格来源

指令编号来自 `CanvasEx::Game_adv` 中的两个 `switch` 表，操作数布局来自各处理方法的 `ByteRead`/`ShortRead`/`UnsignedShortRead`/`StringRead` 调用序列，均取自本作原程序集，不沿用第八作的推测。本作 14 个场景镜像全部逐字节回放通过，标签表项全部落在指令边界。`scn0.bin` 使用 `20050524` 标记且不含标签表与正文区，单独以 `parse_index` 校验。

## 验证

```powershell
.venv/Scripts/python.exe -m unittest discover -s engine/adapters/gmode-20050117 -p "test_*.py"
```

用例直接读取 `games/09-samidare/raw`（本机提取、不进 Git）和 `research/kibu9-assembly.json` 中的原始 SJIS 表。修改 gmode-v2 或本适配器后须重跑本目录与 `gmode-20050817` 的用例；离线通过不代替用户实机验证。

运行时另有离线行为回归与编译期绑定校验，见本作 `bepinex/tests/Run-RuntimeTests.ps1` 和 `scripts/validate_runtime.ps1`。


公共运行时绘制和 UI 实现见 [gmode-v2](../gmode-v2/README.md)。本目录只负责本版本语义；不得复制公共层实现。第九作仍只接入离线解析，后续运行时需按本作方法签名接入。
