# G-MODE v2 公共适配层

第八作（`20050817`）与第九作（`20050117`）的场景脚本使用同一套解码机制：扁平的 `opcode + 操作数` 字节流、脚本前的 16 位小端标签表、大端 16 位数值、以及 100 字节局部缓冲的 NUL 结尾 Shift-JIS 字符串。差异只在**信封、指令表和少数条件操作数**。本目录保存前者，两个 adapter 只保留各自的差异，避免同一套框架被复制多份。

## 内容

- `decode_text`：按 Python codec 名或原始 65537 项 uint16 表解码，两者可互换。
- `Reader`：字节游标，`take`/`number`/`string`/`arg`。`string` 忠实复现原 `CanvasEx::StringRead`：最多 100 字节，遇 NUL 结束，之后**无条件多前进一字节**。
- `parse_commands`：通用指令循环。表驱动固定操作数布局，`special` 提供条件操作数的处理函数，`with_rows` 决定是否为每条指令预置 `rows`。
- `split_script` / `validate_labels`：版本标记与标签表校验；标签必须落在指令边界而不是操作数内部。
- `offset_table`：scratch 容器成员表，`count_size` 区分第八作图片容器的 2 字节成员数和第九作混合容器的 1 字节成员数。

## 引用方式

与本仓库 `engine/tools` 的既有做法一致：使用方把本目录加入 `sys.path` 后按模块名导入。两个 adapter 的 `vm.py`、`container.py`、`image_resources.py` 各自只用一行完成这件事：

```python
sys.path.append(str(Path(__file__).resolve().parents[1] / 'gmode-v2'))
import vm_frame as frame
```

这样每个 adapter 目录仍可被单独 import 或 `unittest discover`，不依赖作品脚本预先设置路径。

## 各版本保留的差异

| 内容 | 20050817 | 20050117 |
| --- | --- | --- |
| 信封 | `FFFF` + 16 位长度 + 逐场景 ZIP | 无信封、无 ZIP，载荷直接以版本串开头 |
| 成员数宽度 | 图片容器 2 字节（`image_resources`） | 混合容器 1 字节（`container`） |
| 正文模型 | `BUNSYOU` 逐行颜色/注音/控制平面 | `BUNSYOU` 三字节设置 + 一条字符串 |
| 独有指令 | `INFO`/`ROORU`/`SIORI`/`RISUTO*`/`SUKUROORU` 等 12 个 | `AME`/`AME_SETTI` 与 8 个 `BUNSYOU_*` |
| 操作数不同的同名指令 | `5`、`40`、`255` | 同左 |

运行时报文以外的差异都要回到对应 adapter，不要把某个版本的正文模型推广到另一个版本。

## 验证

```powershell
.venv/Scripts/python.exe -m unittest discover -s engine/adapters/gmode-v2 -p "test_*.py"
```

本框架的重构必须同时通过 `gmode-20050817`（19 项）与 `gmode-20050117`（11 项）用例。本轮抽取公共框架时以真实语料做了前后指纹比对：第八作 5 个容器成员表 + 59 个脚本解析结果、第九作 1 个成员表 + 15 个脚本解析结果，共 80 项中 79 项逐字节一致。唯一差异是损坏容器（`scratch2.dat` 并非成员表）的报错措辞由 `Duplicate scratch resource` 改为 `Invalid scratch member name`，异常类型仍是 `ValueError`，仓库内没有调用方或测试依赖该措辞。`Reader.string` 的 100 字节回退分支在两个已发行语料上不可达，与旧实现的严格报错不可区分，同样是经指纹确认的等价改动。


## 运行时与作品层

- `src/BitmapFontAtlas.cs`：KBF 字形读取、纹理和材质管理。
- `src/LegacyFontRenderer.cs`：共用字符网格绘制、Latin 显示映射和字形回退。原 `DrawCharImpl` 在两作中一致；`RenderStart/RenderEnd` 不同，始终调用当前游戏的原方法，不能把第八作的双缓冲分支移植到第九作。
- `ui/`：共用 Unity/Socotra UI 翻译、字体和生命周期处理；详见 [UI README](ui/README.md)。作品提供词典、排除项、姓名确认文案。
- `gmode-20050817`：第八作版本适配，保留指令表、正文绑定、协程挂钩、笔记本/分页状态和版本布局。
- `gmode-20050117`：第九作版本适配，保留裸脚本信封、不同指令表和正文模型；目前仅离线解析接入公共框架，尚未完成运行时汉化。
- `games/*`：作品词条、译名、图片选择、特殊谜题、插件入口和安装配置。

KBF3 编码工具、字体源、可复用 UI 图片资产仍位于 `engine/tools`、`engine/fonts`、`engine/ui-assets`，不依赖某个 VM 版本。公共层不引用两侧版本适配器；原 C# 命名空间暂时保留，避免破坏历史插件反射调用。

第八作构建直接编译这里的生产代码，不保留旧文件副本。构建同时运行两个版本的解析测试、公共框架测试、真实程序集指纹/绘制契约检查，以及既有 UI、字体几何、运行时绑定与历史回归。程序集契约测试只确认离线兼容性，不代表第九作完成实机验证。


## 正文和分页的分工

`TextBreaks.Next(text, start, limit, measure, narrow)` 负责找断行位置：标点禁则、英文串和颜文字保持完整，宽度由调用方提供。它不认识 RuntimeRow、SLASH、点击等待或 127 行限制；这些原生语义由 `20050817/NativeDialogueLayout` 处理。这样第九作可以使用自己的逐字记录构造显示行，再复用同一断行算法。

`PageMemory` 保存一个画布会话中的脚本/菜单页组、上次页、各页光标、显式翻页目标；支持更换脚本再回来恢复，无容量淘汰。`20050817/NativePagination` 只绑定字段、计算脚本身份、读取页组定义并把选项标签转换为目标位置。原生挂钩和具体页组识别仍按版本处理。公共层无需 Unity、Harmony 或第八作类型。

公共算法测试另用不同字宽和两套页组验证；第八作的真实菜单回归继续验证原生调用路径，包括显式上一页、退出恢复与脚本重载。


## C# 公共实现清单

| 文件 | 共用职责 | 版本层保留内容 |
| --- | --- | --- |
| `src/TextBreaks.cs` | 正文断行与禁则 | 原生正文表示、等待/换行指令 |
| `src/TextGeometry.cs` | 空格压缩、行宽与双列位置计算 | 字宽参数、画布坐标、原生对齐字段 |
| `src/MenuMemory.cs` | 脚本内容身份与菜单光标/滚动位置记忆 | 菜单身份选择、原生 IL 挂钩 |
| `src/PageMemory.cs` | 页组、显式翻页、退出恢复 | 标签到目标位置转换、页组发现 |
| `src/BitmapFontAtlas.cs`、`src/LegacyFontRenderer.cs` | 字形资源及绘制 | 字体选择和绘制入口 |
| `src/NamedImageRuntime.cs` | 清单验证、图片路由、替换与清理 | 作品图片和尺寸/章节配置 |
| `src/HistoryView.cs` | 历史窗口、布局缓存和滚动显示 | 原生输入暂停、采集挂钩 |
| `src/HistoryState.cs` | 已显示字符去重、历史分段、软键提示状态 | 忽略笔记本的判定、控制码解释 |
| `ui/src/UiLocalizationRuntime.cs` | UI 翻译、字体和恢复 | 作品词典与特殊文案 |

这些文件是生产实现，八作的文本、图片、历史插件分别直接编译所需文件，无本地副本。为避免破坏现有反射调用，部分旧命名空间保留；目录归属和构建引用决定公共实现的位置。

剩余 `CanvasRuntime` 负责 20050817 的缓冲字段、指令与绘制签名；`NativeMenuPosition` 匹配该版本原生 IL；`RuntimePack` 绑定该版本逐行颜色/控制平面。不能把这些挂钩整体套到第九作，后续应由 20050117 适配器转换原生状态后调用上述公共实现。


`src/HistoryAudioMute.cs` 保存并恢复指定 AudioSource 的静音状态，供历史面板使用；不控制全局监听器，也不改变音频播放/回调状态。20050817 适配器选择 `phraseTrack[1]` 音效通道，保留 `[0]` 背景音乐。`Run-HistoryAudio.py` 直接执行生产打开/关闭方法，验证文字播放期间打开历史的静音与原状态恢复。
