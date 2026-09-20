# 《侦探·癸生川凌介事件谭》第十作《永劫会事件》简体中文工程

截至 2026-09-19，正式稿中 9,541 个实际加载文本单元全部译为中文，另保留 309 个不加载的备用副本。正文、姓名、选项、章节文字、外层 UI、图片和历史记录均已接入构建链。最终整作语义门禁和完整补丁构建已通过：8,591 个点击、1,270 个着色片段均有独立审校记录。实机效果由用户验证。

游戏安装路径在系列配置中登记为 `../../GmodeArchivesPlus_kibu10`。仓库为 `Heptagon196/Kibukawa_CHS`，本工程目录为 `games/10-kibu10`。本作基于第八作同系行引擎，只有已证实的直接 BIN、方法签名和指令差异使用薄 adapter，详见 `COMPATIBILITY.md`。

## 本地复现

以下命令均在系列根目录 `translation_workspace` 执行，使用仓库现有 `.venv`。它们不安装补丁、不启动游戏。

```powershell
.\run.ps1 paths --game kibu10
.\.venv\Scripts\python.exe games/10-kibu10/scripts/translation.py check --complete
.\.venv\Scripts\python.exe games/10-kibu10/scripts/check_ui.py
.\.venv\Scripts\python.exe games/10-kibu10/scripts/translation_review.py --export-scenes
```

最后一条只刷新候选与按场景审校材料，不自动批准。正式稿修改后，可用以下命令重建缓存；这会把缓存审校状态重置为 draft，随后必须重新执行最终验证：

```powershell
.\.venv\Scripts\python.exe games/10-kibu10/scripts/translation.py collect --complete
```

完成实际审校、汇总本作点击与颜色基线后，按顺序执行正式门禁与构建：

```powershell
.\.venv\Scripts\python.exe games/10-kibu10/scripts/translation_review.py --strict
.\.venv\Scripts\python.exe games/10-kibu10/scripts/verify_all.py
.\.venv\Scripts\python.exe games/10-kibu10/scripts/build_bepinex.py
```

缺译、未解决审计问题或基线缺失/过期时，正式命令会失败。它们使用公共 BepInEx 构建层并核验输入哈希，不会自行安装。本作已启用，也可运行 `.\run.ps1 build --game kibu10`。当前系列入口的 `verify` 也会调构建脚本；只做离线验证时使用上面的 `verify_all.py`。

开发检查可以显式使用 `verify_all.py --smoke` 或 `build_bepinex.py --smoke`，但不得把 `SMOKE_NOT_RELEASE` 包交付为已完成补丁。不要为了重建译文重新 extract：提取仅用于核对来源，且其状态输出是提取时快照；当前翻译进度应看 `translation-audit.json`。

## 文件与证据

| 内容 | 位置 |
| --- | --- |
| 正式带标签译稿 | `work/dialogue-tagged.json` |
| 本作术语与规则 | `work/glossary.locked.json`、`work/STYLE_GUIDE.md` |
| 分批翻译与交叉审校 | `work/parallel` |
| 原资源指纹、文本位置 | `work/manifest.json`、`originals` |
| 引擎对比与原指令回放 | `research/engine-comparison.json`、`research/source-replay.json` |
| 翻译覆盖与结构检查 | `reports/translation-audit.json` |
| 点击、颜色候选 | `reports/clicks-review.json`、`reports/colors-review.json`、`reports/review-scenes` |
| 正式已审基线 | `work/click_boundaries.reviewed.json`、`research/color-spans.reviewed.json` |
| 外层 UI | `work/ui-*.zh-CN.json`、`reports/ui-check.json` |
| 图片、玩法说明 | `images`、`reports/images_latest.json`、`reports/help-pages_latest.json` |
| 历史记录离线构建 | `reports/history-build.json` |
| 已有开发验证 | `reports/verify-smoke.json`、`reports/runtime-pack-smoke.json` |
| 最终离线验证 | `reports/verify-all.json` |
| 最终包与校验信息 | `reports/build_latest.json`、`out/CHS_*/build_report.json` |

主插件使用中文像素字体和内存文本替换；原脚本字节及存档偏移保持不变。公共图片替换插件覆盖命名图片、标题美术和玩法说明，公共历史组件通过本作绑定记录中文和彩色文本。原日文注音在中文行禁用。离线单元测试和哈希校验不能代替实机显示验收。

最终完整包应包含主汉化插件、图片替换插件、历史记录插件、字体、许可与 BepInEx 框架。完整包已生成，由用户依包内 `README_Kibu10_CHS.txt` 手动安装与验证。本工作不修改前作译文，不自动安装或操作游戏窗口。交付状态见 `TRANSLATION_COMPLETE.md`。

## 本次交付

正式包：`out/CHS_20260919_231258_328679800/Kibu10_CHS.zip`。共 92 个文件、2,010,764 字节。

SHA256：`3e1a232bfcd70efd30bae7e3c4c040e2cdc9b1a1caf7b39d047a4ded407d3238`。

包含公共 BepInEx 框架、主汉化/图片/历史三个插件、字体与许可。未安装；由用户验证实机显示、菜单与存档。

2026-09-19 0.1.1 修订已安装：修复图片插件启动过早；正文与正文姓名栏16px，其余文字保留原版字号；一张完整艺术字母版程序拆分共用于三个标题；恢复bg21原图。旧文件已备份，未操作游戏窗口。见 reports/title-font-repair.json、images/composed/README.md 和 reports/install_latest.json。

2026-09-20：0.1.3 排版规则已实现并安装。中英文间距仅影响像素坐标；固定 jieba 与术语保护、原文语义硬边界、整体优化断行；全屏保留原行位，不追加点击。最新包：`out/CHS_20260920_211221_311614700/Kibu10_CHS.zip`。详见 [排版规则](LAYOUT_POLICY.md) 与 reports/layout-policy-applied.json，实机效果待用户验证。

2026-09-20：0.1.5 完成发布级 QA 修复。修正空目标行、标点、省略号、强调色范围、语义与字谜问题；INFO 严格按原生全角（含全角空格）12px、半角 6px 度量，并将 240px 容量检查纳入发布门禁。验证和安装记录见 `reports/qa-remediation-20260920.md`。
