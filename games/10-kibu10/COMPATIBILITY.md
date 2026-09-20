# 第十作《永劫会事件》兼容性记录

本记录更新于 2026-09-19：正文、姓名、选项与章节文字的 9,541 个 active 单元已全部译入正式稿；运行时、外层 UI、图片与历史记录构建链已实现。最终语义门禁和正式完整包已通过离线验证，见 reports/verify-all.json 与 reports/build_latest.json。尚未进行实机验证，不自动安装、不启动或操作游戏窗口。

安装路径相对于系列根目录登记为 `../../GmodeArchivesPlus_kibu10`，工程为 `games/10-kibu10`。标题采用“永劫会事件”。原始开场“第９弾”按手机版编号译为“第 9 作”，不据此改动 Steam 第十作的工程编号。

## 引擎依据与薄适配层

以第八作为主要对照。两作同为 `20050817`，原始 SJIS 映射表一致；正文、颜色、控制符、注音行平面可复用第八作。规范化 CanvasEx IL 对比记录在 `research/engine-comparison.json`：63 个方法相同、48 个共同方法不同，第八作独有 123 个、第十作独有 23 个（包含协程生成类型，不代表指令数量）。

新增 `engine/adapters/gmode-20050817-direct` 仅针对已确认差异：

- 第十作使用直接 BIN 脚本容器，并由普通方法 `Game_adv` 执行主循环。
- `KOMANDO`（opcode 5）参数是短整型；`HAIKEI_SETTI`（40）只有标志及有条件出现的文件名。
- 73 是 `SABUTAITORU`，格式为 `Bs`；76 是 `SINARIOSENTAKU`，无参数。
- 直接运行时与菜单记忆挂钩匹配本作方法签名；不套用第九作正文运行时。

`vm.py` 直接加载第八作行解析器及其公共读取框架。构建时复用第八作 RuntimePack，并在本作 generated 目录生成允许 opcode 73 的版本，不修改前作源码。字形、排版、菜单公共能力与历史基础模块继续复用。原脚本字节与偏移不变，译文在内存中绑定，避免改变跳转和存档地址。

原始 Assembly-CSharp SHA256：`4ba838ad7a619d70803f17ae11c951811835af944f4faee69c91d46341816aef`。启动插件会校验原资源指纹，版本不符时拒绝启用。

## 提取、翻译与构建证据

- 40 份脚本、19,834 条指令完整解析，标签指向有效指令边界。见 `reports/extraction.json`、`research/source-replay.json`。
- 正式稿 `work/dialogue-tagged.json` 共 9,850 单元，9,541 个 active 单元全译；另有 309 个 inactive 副本，位于 scratch4 的 start/define/append/help。游戏对这四个名称固定读取 file 资源，副本保留审计，不重复翻译。
- `reports/translation-audit.json` 当前记录 pending=0、结构有效、findings=0。这是覆盖与结构检查，不等于语义审校或实机验收。
- 13 批翻译与交叉审校材料位于 `work/parallel`。正式点击与颜色基线必须由实际复核结果汇总，再由 `scripts/translation_review.py --strict` 检查；不得直接把候选报告确认为已审。
- `scripts/build_bepinex.py` 使用公共 `engine/bepinex/build.py` 完成框架依赖校验、编译、组包和归档，主插件为 `Kibu10ZhCN.dll`。独立的历史和图片插件一并纳入包，不自行复制另一套 BepInEx 构建层。
- 外层 UI 见 `work/ui-*.zh-CN.json`；`reports/ui-check.json` 当前记录 15 个本地化键、58 个精确文本项，扫描了 2,532 个程序集字面量和 91 个序列化出现位置，errors=0。
- 图片构建见 `reports/images_latest.json`：16 条命名资源路由、12 条亮度路由、5 项美术资源及 2 项原生英文标志。玩法说明 4 页均已翻译，见 `reports/help-pages_latest.json`。这些报告不表示实机显示已验证。
- 历史插件复用公共历史缓冲、彩色排版与显示模块；`reports/history-build.json` 记录离线测试通过，runtime_tested=false。
- 已有 `reports/verify-smoke.json` 和 `reports/runtime-pack-smoke.json`。开发包记录 36 个实际脚本、8,744 个显示单元和 797 个字符串条目，无缺译；正式构建已重新生成 reports/runtime-pack.json 和 build_latest.json。

原游戏及前作 work 文件的保护校验由构建与验证脚本执行；已有 smoke 报告记录两者未改。所有最终结论以同一次正式构建的哈希报告为准。project.json 与 series.json 已按最终离线报告启用本作；runtime_tested 仍为 false。

命令及完成条件见 `README.md` 与 `TRANSLATION_COMPLETE.md`。

最终审校：8,591 点击、1,270 颜色全部匹配已审基线；23 项 Python 测试及正文/UI/菜单/历史运行时测试通过，实际游戏 SJIS 解码器绑定 40 BIN，通过 8,498 段完整正文离线重排。16px 字体 3,716 字、12px 字体 2,832 字均无缺字。

本次构建前后原游戏和前作 work 哈希相同。对比会话开始快照时，另观察到第九作 8 个文件发生并行工作区变化，记录于 reports/protected-files-session-comparison.json；本任务未写入或回滚这些前作文件。

公共文风检查器的 3,002 条提示另有解释：2,740 条引号提示来自其仅拼接 opcode 72、将本作 opcode 255 正文拆为独立槽的限制，完整发言与分支已按 13 批原指令上下文独立审校；262 条空白提示对应 162 个单元，逐项复核均为原作标题、空白行、字谜或残笔排版。详见 work/style-audit-review.json 与 work/review-summary.json，未把通用检查器宣称为零提示。
