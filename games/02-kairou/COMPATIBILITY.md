# 第二作接入记录

登记作品：第2卷《海楼馆杀人事件》，游戏资源标识 `KAIROU` / `kairou.res`。
检查日期：2026-09-06。所有检查离线进行，没有安装补丁或启动游戏。

## 路径与启用状态

- `series.json` 项目路径：`games/02-kairou`。
- 安装路径：`../../GmodeArchivesPlus_kibu2`，相对于系列配置文件。
- `default_game` 仍为 `kibu1`；`kibu2.enabled=false`，禁止正式 build/verify/install。
- 待审作品仅开放 paths/status/extract/probe；probe 是构建验证包，不是汉化发布包。

## 静态对照

| 项目 | 结果 |
| --- | --- |
| Unity | 两作 globalgamemanagers 均为 2019.4.9f1 |
| 平台 | 第二作 kibu2.exe 的 PE Machine 为 AMD64；存在 MonoBleedingEdge 和 Managed，无 GameAssembly.dll |
| 第一作原程序集 SHA256 | `4fdd00886cecdae1569aec334302dd21277ef1db1a09b73a62ebe8f21a1e191e` |
| 第二作原程序集 SHA256 | `92147a074054df35f0904a2db3ec4b44980a9e147df0ad3eea8b768443a3086c` |
| 方法体 | 两作各 4,011 个，规范化 IL 对比有 4 处变化，无新增方法 |
| 字段声明 | 3,219 个字段的名称、类型和属性一致；不代表所有静态初始化数据或资源一致 |
| 字符编码 | 131,074 字节的原游戏 SJIS 映射表完全相同 |
| 指令定义 | StreamingAssets/file 中 define 字节完全相同 |
| 场景解析 | scn0–scn9、subscn_1–2 共 20,948 条指令；1,351 个跳转参数全部落在有效指令边界或终止标记 |
| 文本容量 | 构造方法一致，Text 为 9 个 20 字符缓冲；这不等于一屏能显示 9 行 |

`CanvasEx.Read`、`Script`、`<Script>d__256.MoveNext`、`ExeText`、`Jump` 以及字体、菜单相关未变方法可作为复用依据。这里只证明对应 IL 一致，没有执行 Harmony 挂钩或验证中文显示。

4 处变化：

1. `CanvasEx.Play`：默认音效索引 14 → 12。
2. `CanvasEx..cctor`：应用/资源名变更，声音表从 15 项改为 13 项，多个音效资源名变化。
3. `CanvasEx.Paint`：出现 70 → 64、140 → 128，以及图像定位 19 → 21、43 → 41。
4. `CanvasEx.<Run>d__246.MoveNext`：画面位置计算中的 141/140 改为 129/128。

因此保留 `gmode-v1` 作为候选适配器，不复制第一作的聊天区间、名单区间、帮助图或排版结论。完整 IL 与资产清单在本地忽略目录 `research/`，不提交原程序集或解包二进制。

## 提取与构建

首次提取 10,404 条记录：7,988 条待译，2,416 条为暂时排除的技术/模板候选。其中场景非空字符串 7,894 条。提取时译文字段均为空；现已完成待译文本初稿及逐章交叉审校，见 [文本进度](TRANSLATION_STATUS.md)。

覆盖场景字节码、本作姓名/子场景、日文 localization、Unity MonoBehaviour 中对齐的 CJK 字符串、程序集 ldstr。图片、任意原生二进制和技术候选项的人工判定仍待处理。

公共构建层 `engine/bepinex/build.py` 原样复用：校验已有 BepInEx 5.4.23.5 x64 缓存，引用第二作 Managed 编译、组装完整框架并校验 ZIP。第二作插件身份为 `local.kibu2.bootstrap`，进程过滤为 `kibu2.exe`；没有第一作插件程序集依赖。

同时编译公共 TranslationCatalog、TranslationPackReader、BitmapFontAtlas、LegacyFontRenderer 和 MenuSelectionMemory。入口仅写一条日志，不调用这些组件，不安装翻译挂钩。DialogueReflow 尚依赖作品级 ChatLayout/FixedCardLayout，本阶段没有伪造策略或引入第一作地址来凑齐编译。

本地构建结果见 `reports/bootstrap_latest.json`。`out/` 中的 ZIP 明确标为 `NOT_TRANSLATION`；不作为实机汉化测试包交付。

## 已执行验证

- 系列路径配置测试 5 项通过，公共 BepInEx 构建层测试 6 项通过（网络响应模拟）。
- 第二作引用编译、插件身份/进程过滤检查及 ZIP 完整性校验通过。
- 实际调用 build、verify、install 均被待审状态拦截，没有进入安装步骤。
- 模拟本地提取报告缺失后，重复 extract 成功恢复；cache、manifest、术语锁的 SHA256 全部不变。
- 两次探针构建均验证第二作目录及第一作已跟踪文件未变；第一作许可文件的已有改动保持原状。
- 独立子 agent 完成工程只读审查及恢复逻辑复核；另一个子 agent 整理术语候选，尚未将新名称标成已批准。

## 后续启用条件

建立第二作专属挂钩入口与原文地址匹配，复核新术语和特殊页面，逐章翻译审校，再完成真实指令回放、点击边界与中文重排检查。帮助图片、标题和名单独立检查。上述离线检查完成后生成正式测试包，由用户验证实机效果并记录结果。

原文件指纹保存在本作 manifest；各次提取/探针构建前后检查第二作全目录和第一作已跟踪文件哈希。未改第一作译文；已有字体许可文件改动保留。
