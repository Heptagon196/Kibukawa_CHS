# G-MODE 20050817 适配器

第八作原始 CanvasEx.LoadScenario 使用 20050817 场景格式，与 gmode-v1 的 Read/ExeText/Script 协程和 define 参数表不同。本目录提供该引擎的解析、译文绑定和显示运行时；目前以第八作原程序集和场景验证，不能据此宣称支持未经检查的后作。

## 与 gmode-v2 的分工

版本中立的脚本框架（字节游标、SJIS 解码、标签表、通用指令循环、scratch 成员表）已抽到 `engine/adapters/gmode-v2`，本目录只保留本版本特有的部分：`FFFF`+长度+ZIP 信封、指令表、逐行颜色/注音/控制平面与红宝石字形，以及 `5`/`40`/`255` 的条件操作数。`vm.py` 对外仍导出 `NAMES`、`FORMATS`、`CONTROL_NAMES`、`decode_text`、`Reader`、`parse_script`、`parse_bin`，调用方不受影响。公共框架的重构须同时回归本目录与 `gmode-20050117` 的用例。

## 职责

- container.py、vm.py：原始容器、场景指令和标签解析。
- RuntimePack.cs、runtime_pack.py：标准 translations.bin 与原始场景绑定；不修改脚本字节或存档地址。
- src/CanvasRuntime.cs：运行时基类、引擎挂钩、显示缓冲替换、滚动视口、正文与 INFO 绘制。
- src/NativeDialogueLayout.cs：按字符重排正文，保留颜色与控制事件。
- src/NativeChoiceMemory.cs：扩展原生记忆表到可返回的文字菜单，保留真正的返回目标。
- 点阵图集与绘制实现已迁至 `../gmode-v2/src/BitmapFontAtlas.cs`、`LegacyFontRenderer.cs`。
- src/RuntimeLayout.cs：作品向运行时提供排版策略的接口。

作品目录保留 BepInEx 插件身份和启动/销毁入口、原文件指纹、译文与脚本身份表、字体文件选择、排版策略、小字体页面范围、Unity UI 文案与本作标题图片规则。插件继承 CanvasRuntime，并传入 UI 字典与 RuntimeLayout；适配层不引用本作 UiLocalizationData 或 ScriptIdentityData，不含本作插件 ID、版本和安装路径。

构建继续使用 engine/bepinex/build.py，直接编译此处源码，不在作品目录保存副本。历史记录与通用图片替换仍使用各自公共层。保留已有图集类的 Kibu1ZhCN 和译文模型的 Kibukawa8.Runtime CLR 命名空间，以避免本次目录重构同时改变它们的调用接口；Canvas 运行时使用 Kibukawa.Engine.Gmode20050817。

## 验证

第八作的真实程序集绑定、全场景回放、字体几何和原生菜单 IL 用例保存在 games/08-kibu8/bepinex/tests，直接编译适配层生产源码。修改本适配器时运行第八作完整构建；以后有其他作品选用本适配器时，须一并回归。原 gmode-v1/gmode-dual-v1 及前作译文未改动。离线通过不代替用户实机验证。

## 图片和历史记录构建边界

- `command_icons.py`：接收原始 48×24 双状态图、同尺寸修补底图、两个字的文案及原生 10px 字形；负责调色板映射、保护图标、描边和绘制。不读取作品目录或下载字体。
- `image_resources.py`：解析 scratch 图片容器，验证偏移、长度、重复名和尾部；解析 ResourcesManager 章节根及 Resources 纹理路由。数据目录和章节数由作品传入。
- `../gmode-v2/src/NamedImageRuntime.cs`：校验原资源指纹、注册命名图片路由、按章节替换与资源释放。作品通过子类提供游戏 ID、章节数及专用美术回调。
- `src/HistoryRuntime.cs`、`HistoryCapture.cs`：20050817 绘制跟踪、笔记页排除、姓名及颜色快照、历史面板输入与生命周期。历史缓冲、彩色排版和输入策略继续引用 `engine/history/src`；姓名翻译由作品回调提供。

原生 BDF 解析位于跨引擎公共工具 `engine/tools/bdf_font.py`，与现有 Unifont/Z Labs 读取工具同层。字体选择、下载锁、授权文件安装以及本作所需字符收集由作品构建入口负责。

第八作仍保留按钮文案和修补底图、笔记背景合成规格、标题菜单几何/素材规则、插件身份、UI 字典、脚本身份、译文审校和安装流程。这些不属于当前 VM 的通用行为。构建入口只调用适配层，不复制算法源码。`test_command_icons.py` 验证用户确认的全部十个按钮、二十种状态的像素哈希；历史测试直接编译本适配层源码。

底部调查短菜单由 `menu_constraints.py` 根据 KOMANDO / CHOUBUN_KOMANDO 等声明区分；第八作译文审计限制其标签不超过 6 个字符。长句选项与原始 start 音效测试菜单不套用调查标签限制。

全屏顶部的项目符号列表（MojiHani_tate=1，首行以「・」开头）采用固定 x=10、y=24、正文行距，防止逐项淡入时居中基准移动留下重影，并避开 INFO 顶栏。回归使用真实目录各阶段译文；普通全屏段落和居中标题保留原有策略。

英文数字显示：为保留原 VM 的单字符颜色/控制索引，translations.bin 内仍以全角码点占位。BitmapFontAtlas 显示时映射为原生 ASCII 字形；正文拉丁字母/数字前进 9px、汉字前进 17px，顶栏分别 7px/13px。NativeDialogueLayout 按实际宽度换行，并尽量不在英文单词内部断行。历史记录输出半角字母数字。内部占位不等于显示全角字形，不应直接删除 fullwidth 编包转换。

## 跨版本公共层（0.5.58 起）

Unity UI 显示挂钩、字体恢复和生命周期管理已移到 `engine/adapters/gmode-v2/ui/src/UiLocalizationRuntime.cs`，使用说明见 `engine/adapters/gmode-v2/ui/README.md`。作品仍提供译文表、技术字符串、姓名确认句和字体候选。该模块不属于 20050817 VM，也不共享各版本不同的 RenderStart/RenderEnd。

KBF3 索引与 RGBA 编码已移到 `engine/tools/kbf3_atlas.py`，使用说明见 `engine/tools/README.md`。第八作 UI 字库和笔记姓名读音字库都调用它；字体来源、字符收集与图集排列仍由作品控制。

对白引号颜色：`RuntimePack.cs` 在原文色段恢复后，把译文新增的外层双引号从关键词高亮中分离为正文白色；原文自带的引用与特殊色文本保留。`runtime_pack.py` 用同一规则生成离线颜色参考，完整构建逐行对照两者。译文标签、原始脚本和控制事件不变。


公共运行时绘制和 UI 实现见 [gmode-v2](../gmode-v2/README.md)。本目录只负责本版本语义；不得复制公共层实现。第九作仍只接入离线解析，后续运行时需按本作方法签名接入。


菜单标题（`menu_prompt`）与短选项均受六字上限检查，标点计入字符数。作品 `translation.py check --complete` 报告 `menu_title_max_6`，完整构建遇到超长标题即失败。长选项正文不套用此上限。
