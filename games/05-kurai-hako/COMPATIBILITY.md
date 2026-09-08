# 第五作接入记录

已阅读 series.json、series/style.md、series/glossary.json 和公共 BepInEx 构建说明。原文标题为《昏い匣の上》，中文标题为《暗匣之上》；项目 ID 为 kibu5。

## 路径与边界

- 项目：`games/05-kurai-hako`。
- 安装：`../../GmodeArchivesPlus_kibu5`，相对于 series.json。
- Git remote 已核对为 `https://github.com/Heptagon196/Kibukawa_CHS.git`；本轮未提交、推送或发布。
- 独立术语快照继承系列表，独立 STYLE_GUIDE.md 继承现行指导；没有覆盖或修改前四作译文。
- 正式适配已通过离线验证：enabled/release_ready/hooks_ready=true，runtime_tested=false；可经系列入口构建、验证、安装供用户测试。

## 引擎证据

第五作是 Windows AMD64 / Unity Mono，存在 MonoBleedingEdge 和 Managed 程序集，没有 GameAssembly.dll。使用单套 `appli1.CanvasEx`，不采用第四作的双篇上下文；登记独立适配名 `gmode-appli1-v1`，生产挂钩已实现，并通过原始程序集与全部指令回放验证。

Assembly-CSharp.dll SHA256：`2db6c7b595c91b1a7cc4937befe50e459f3769d68ccf600556f29e63deb5c4c2`。

原始程序集含 4013 个有方法体的方法。与已锁定原始程序集比较：SJIS 解码表与前四作一致；指令定义与第一、第二作一致。资源归档为 `kuraihako.res`，完整解析 scn0–scn6 和两份 subscn，共 16386 条指令；逐条检查原始游标、字符串边界与跳转目标。

命名空间与编译器协程编号归一化后，56 个 CanvasEx 方法中：51 个与第一作一致；52 个与第二、第三作及第四作 appli1 一致。Read、Script、Jump、ExeText 对应 IL 一致。差异包括：

- 第一作 Run 的高度常量 141/140 在第五作为 129/128，与第二、第三作相同。
- Init 内有 4096 → 3072 的资源容量常量差异（相对第一作），不能当成文本缓冲大小。
- Paint 绘制逻辑不同，需要逐界面检查，不能复用前作固定名单或标题地址。
- Play 音效索引和静态资源名、音效表发生变化。
- StGraphics 增加裁剪填充缓存字段和方法，绘制侧仍需独立验证。

归一化只是静态对比，不证明运行时兼容，也不覆盖嵌入 RVA 数组、图片或实机效果。完整 IL 差异保存在本机 research/normalized-engine-comparison.json；可用 compare_engine.py 重建。

## 提取与公共构建

提取生成 8625 条定位记录：6209 条待翻译/筛选、2416 条技术或模板候选暂排除。初次提取时译文为零；现已处理全部6209条选中记录（6202条内容/界面、7条保留调试标识），完成文本初译及审校，详见 TRANSLATION_PROGRESS.md。候选数不当成最终翻译数。正文约 6115 个字符串槽，包含场景菜单标识等仍需复核项；姓名注音、图片帮助页和固定标题要另行处理。

复用 engine/bepinex/build.py 的依赖校验、编译、组包和 ZIP 校验；固定配置为 mono-win-x64-5.4.23.5。探针编译 engine/core 以及公共字体、菜单组件，离线核对 Kibu5Bootstrap 程序集、local.kibu5.bootstrap 插件 ID、kibu5.exe 进程过滤器。不复制前作运行时入口或固定地址，未接入 DialogueReflow。

验证完成：首次提取及重复提取成功，已有 cache/manifest 按字节保留；原游戏及前四作项目文件全量哈希保持不变；5 项路径测试与 6 项公共构建测试通过；探针编译和组包通过。游戏未安装探针、未启动窗口，实机交给用户验证。

探针输出（本机忽略文件）：`out/bootstrap_20260908_004957_942532800/Kibu5_Bootstrap_NOT_TRANSLATION.zip`。这是无翻译挂钩的构建验证包，不是汉化补丁。

## 后续

1. 按完整发言与分支复核提取候选、姓名和新专名，锁定本作增补术语；不自动处理场景标识及注音。
2. 实现单套 appli1 的上下文读取挂钩，用第五作真实指令回放验证，再接入公共 DialogueReflow 与字体。
3. 独立处理标题、制作名单、帮助图片及第五作绘制差异。
4. 已完成提取文本初译及审校；完成上述运行时适配和离线验证后生成供用户实机确认的补丁。

复现命令（仓库根目录）：

```powershell
.\run.ps1 paths --game kibu5
.\run.ps1 extract --game kibu5
.venv/Scripts/python.exe games/05-kurai-hako/scripts/compare_engine.py
.\run.ps1 status --game kibu5
.\run.ps1 probe --game kibu5
```

## 正式适配进展

本作bepinex/src接入公共DialogueReflow、BitmapFontAtlas、LegacyFontRenderer及MenuSelectionMemory。图片替换仅四张帮助图；标题图片按用户最新指示交另一agent，未纳入本包。原始Paint坐标保留。完整离线检查及安装记录见TRANSLATION_PROGRESS.md和reports。原游戏窗口未启动。
