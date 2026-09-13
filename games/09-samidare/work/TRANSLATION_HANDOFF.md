# 第九作翻译交接

> **中文译文与本作规则、术语已于维护者要求下全部移除**（备份：`out/translation-backup-<时间戳>.zip`）。
> 删除内容：`work/dialogue-tagged.json` 的全部 `target`/`runs`、`work/parallel/`、`work/STYLE_GUIDE.md`、
> `work/user_prompt.md`、`work/ui-localization.zh-CN.json`、`work/glossary.locked.json`、`scripts/build_glossary.py`、
> `texts/`。**保留内容（换译者后仍然需要，且不属于译文）**：7,506 条原文提取、`work/emphasis.json`（157 行行内变色切分）、
> `research/ruby-readings.json`（读音研究）、`work/ui-source.json`（界面原表）、引擎适配器、运行时 C#、
> `scripts/translation_batch.py`（含独立复核闸）、`scripts/check_ui.py`、打包链，以及已确认标题。
>
> 因此下面第 2 条里提到的 `STYLE_GUIDE.md`／`user_prompt.md` 已不存在，第 3 条提到的 `glossary.locked.json`
> 与 `ui-localization.zh-CN.json` 需要重新建立。发布打包在 `work/ui-localization.zh-CN.json` 缺失时会明确报错，
> 不会打出半成品。

已阅读系列配置、翻译指导与公共术语表。本作安装相对路径为 `../../GmodeArchivesPlus_kibu9`，原文标题 `五月雨は鈍色の調べ`（证据见 [`../COMPATIBILITY.md`](../COMPATIBILITY.md)），中文标题已由用户确认为「五月雨是铅灰的旋律」。公共术语与本作 `glossary.locked.json` 同时适用；本作表尚未建立条目，也没有可以提升到公共表的定译。

标题确认后，「鈍色」这一母题在正文里统一作「铅灰」：`鈍い色を一面に広げ、` → 「将那铅灰色铺满天空，」、`この鈍色の空は、` → 「这片铅灰色的天空」，与标题一致。

本轮只完成引擎核对、原文提取和公共构建层探针，没有翻译正文，也没有建立点击单元基线。不要用第八作或前七作的译文、术语、点击基线冒充本作材料。

## 引擎结论

本作使用 `20050117` 场景格式，与 `gmode-v1`、`gmode-20050817` 都不同：容器没有 `FFFF` 信封与逐场景 ZIP，正文用「三个设置字节 + 一条字符串」的 `BUNSYOU`，颜色、速度、注音和透明度由相邻指令改变逐字状态。指令框架与第八作重叠很大（38/48 编号同名、36 个布局相同），因此公共框架抽到 `engine/adapters/gmode-v2/`，本作 adapter 只保留指令表、三个条件操作数和裸信封；运行时挂钩不新增，也不复用第八作的协程挂钩。

指令编号来自 `CanvasEx::Game_adv` 的两个 `switch` 表，操作数布局来自各处理方法的读取调用序列。14 个场景镜像全部逐字节回放通过，标签表项全部落在指令边界。

## 原文与界面材料

- 剧情：`raw/scratchpad/`（9 个场景 + `define.bin` + `start.bin` + `scn0.bin`）与 `raw/file/`（`c0_00`/`c0_01`/`c1_00`），共 15 个 `.bin`、204,848 字节。
- 素材：`raw/` 共 146 个成员、405,957 字节，含 122 个 `.gif` 与 9 个 `.jpg`；清单见 `research/material-inventory.json`。
- 界面：`originals/kibu9_Data/StreamingAssets/localization` 的 TextAsset `Localization` 为 CSV，列为 `Key`/`ja`/`en`，含菜单、对话框、排行榜等文案；`en` 列只作参考，不作为译文来源。
- 图片：`scratch1.dat` 内的 122 个 `.gif`/`.jpg`，含 `title.gif`、`menu00.gif`、`menu01.gif`、人物立绘与背景。尚未生成中文替换图。
- 音乐/音效：`scratch2.jar` 内 24 个 `.mld`，`file` 包内 `title.mld`。不涉及译文。

## 下一步

1. ~~实现 `gmode-20050117` 运行时~~ 已完成**正文行、说话人姓名、菜单项、界面文案、历史记录、菜单记忆与行内强调**（`BunsyouStock` 整行替换、`NAMAE_SETTEI`/`SENTAKUSI` 的 `StringRead` 首条替换、`Localization::Get` 按 key 返回中文、软键标签原地替换、`KibukawaHistory.dll` 按段采集、`NativeChoiceMemory` 扩展原生记忆表到可取消文字菜单、`BUNSYOU_IRO` 逐色段写入）。离线回归与 46 + 23 项绑定校验通过，冒烟包可打包。剩余：图片替换。这些应继续接入 `gmode-v2` 公共层，不要从第八作复制实现。
   - **行内强调**：本作颜色是**逐字状态**而非内联标签，实测 **157 行**（168 处）在行中被 `BUNSYOU_IRO` 改色，高亮的是推理关键词或人名。把整行塞进首个片段会让强调失效（改色指令只作用到空片段），因此这类行按色段打包：`target` 用 `\x01` 连接各色段（`runtime_pack.RUN_SEPARATOR` / `RuntimePack.RunSeparator`），运行时把每个色段写入该颜色生效的那个 `BUNSYOU` 片段。切分表在 `work/emphasis.json`，译者须为这些行给出 `runs`。**共享打包格式未改动**，`engine/core/TranslationPackReader.cs` 原样读取 `target`。
2. `work/dialogue-tagged.json` 是**正式对话译稿**：7506 条（7298 正文行 + 34 姓名牌 + 174 菜单项），字段 `script`/`kind`/`offset`/`source`/`target`/`limit`/`fragments`（带行内强调的另有 `runs`）。可读对照见 `texts/<脚本>.txt`（本机阅读用，不进 Git）。重新 extract 会按 `(script, offset)` **保留已有译文与色段**、只刷新源文。**正文行不得超过该行的 `limit`，姓名牌 7 字、菜单项 11 字**，构建时强制校验并报出脚本与偏移。
   - 翻译与写回走 `scripts/translation_batch.py`：`split` 生成 `work/parallel/<脚本>.src.json`，`slice` 切并行批次，译者只产出 `*.trans.json`，**由主控串行 `apply` 写回**（并行者绝不写 `dialogue-tagged.json`）；`apply` 硬校验条数、偏移、字数上限与色段对齐，`check` 报告覆盖率与问题。
   - 项目级规则见 `work/STYLE_GUIDE.md`（引擎硬约束）与 `work/user_prompt.md`。
3. 翻译 `Localization` 界面表（`work/ui-localization.zh-CN.json` 尚未建立，发布打包依赖它），并处理标题图与菜单高亮图。
4. 首次点击单元基线必须逐单元人工对照后建立，不得自动确认。
5. 术语确认后归并到 `series/glossary.json`。

## 约束与并发情况

用户约束：不操作游戏窗口，不修改前作译文，实机效果由用户验证。本轮只写入 `games/09-samidare/`、`engine/adapters/gmode-20050117/`、`series.json` 和根 `README.md`，未安装补丁，未提交或推送。

提取期间 `games/08-kibu8/reports/installation_latest.json` 被其他会话改写（记录已是 0.5.59）。该文件属第八作且被 Git 忽略，本任务未读写，也不据此回退任何内容。
