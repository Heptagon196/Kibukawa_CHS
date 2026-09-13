# 第八作翻译交接

已阅读系列配置、翻译指导与公共术语表。本作安装相对路径为 `../../GmodeArchivesPlus_kibu8`，标题暂译“假面幻影杀人事件”。公共术语与本作 `glossary.locked.json` 同时适用；本作新称呼仍保留 provisional，不推定未揭晓的身份、性别和汉字姓名。

本轮已完成 16,636 条剧情/脚本菜单及 149 处界面文本初译。22 批全部独立交叉审校，修订决定见 `review-decisions.json`，统稿记录见 `coordinator-refinements.json`，审阅覆盖与最终摘要见 `review-summary.json`。批次源文和译文均保留，`dialogue-tagged.json` 为正式带标记稿，`cache.json` 为兼容汇总。运行 collect 会以批次和三个 UI JSON 覆盖汇总，因此后续改文须同步对应批次。

控制码、颜色和物理行标记保持原有顺序；这只证明结构一致，不证明中文排版或点击展示效果已验证。不要建立前作格式的虚假点击/颜色已审基线。颜文字中的原文挥手符号允许精确保留。技术哨兵、模板和调试界面共 64 处不进入可见文本完成率。

本作确实使用不同的 20050817 VM。离线 container.py/vm.py 已能完整解析 59 个 BIN，8 项测试通过；原始元数据在 research/source-replay.json，格式与控制时机研究见 research 中两份说明。公共 BepInEx 构建层已复用，现有输出仅 bootstrap，不是汉化补丁。

下一步是按新 VM 接入运行时译文、中文字体与排版，再处理图片和历史记录。尤其注意控制码在字形之后、ruby 为字图索引、StringRead 的局部缓冲，以及相同场景名在不同分卷中必须分别定位。最终实机验证由用户完成。详见 ../COMPATIBILITY.md。

用户约束：不操作游戏窗口，不修改前作译文。本轮 21 个前作译文/术语文件及 178 个原游戏文件哈希一致。仓库中第七作和公共术语存在其他任务的未提交改动，须保留，不回退或混入本作提交。本轮未提交、推送或安装补丁。

## 0.2.0 构建安装续记

已完成运行时显示缓冲、菜单、姓名牌/书签最终绘制、INFO作用域替换与中文像素字库。核心组件见 ../bepinex/src/Plugin.cs；构建和带备份安装入口见 ../scripts/build_bepinex.py、../scripts/install_patch.py。最新包及安装记录分别位于 reports/build_latest.json、reports/installation_latest.json。实机尚未验证，图片和独立历史扩展未适配。原始 Script/Pos/LabelIndex 与持久化日文姓名/书签保持不变。

构建时进一步统一了33处本作同名地点、章节和姓名标签；记录见 build-terminology-fixes.json。之前 review-summary.json 是初译轮快照，其批次摘要早于这些命名修订；当前构建以正式译稿及最终 runtime.bin 指纹为准。无需重跑早期 prepare_translation 或覆盖已完成批次。

0.2.0 测试补丁已安装，36个新增文件哈希验证通过，178个原游戏文件不变。恢复清单：`installations/20260911_222058_4ff7d570/installation.json`。此前段落中的未安装/目录只读描述指初译轮；本次安装已获用户明确授权。期间第七作译文有其他任务并发变更，本任务未写入前作文件，不能把前作当前哈希与早期基线差异算作本次修改。

## 0.3.0 完整包续记

标题三篇、菜单高亮三项及封面已制作，图片替换插件1.2.0、历史记录插件1.6.2已接入同一构建入口。历史只收录实际绘字，保留姓名颜色并去重；不提前显示未读对白。公共图片及历史核心源码复用；本作入口位于 bepinex/images、bepinex/history 和 bepinex/src/ImageReplacementPlugin.cs。完整包强制包含系列 required_plugins，共54个文件。最新实际安装状态以 reports/installation_latest.json 为准。仍未操作游戏窗口，所有实机显示和输入检查交由用户；不要将离线测试标记为发行验收。

## 0.3.1 加载提示漏译修复

用户截图中的“データ確認中…”已有译文，但 PaintDocomo 调用 Ds_sub 后先拆单字再进入 DrawString，因此整句匹配无法生效。现于 Ds_sub 参数入口替换已收录的完整界面文案，之后由原方法计算居中并绘制双层阴影，保留存档及游戏资源。未新增 adapter，未修改前作译文。

新增 BeforeShadowString 离线回归：修复前报告 Missing pre-split Ds_sub localization hook，修复后确认“正在检查数据……”及未知字符串保留；绑定检查同时核验真实 Ds_sub 签名及 Substring 拆字路径。完整构建、13项解析测试、运行时和历史测试通过。0.3.1 已安装，54个补丁文件校验通过，原游戏文件不变。备份记录 installations/20260912_160021_27122a75/installation.json。未操作游戏窗口，实机效果仍待用户验证。

## 0.3.2 标题菜单与字形

三篇标题图的“杀”字通过内置image_gen逐张纠正并在240×240尺寸复核；生成原稿和提示见 images/GENERATION.md。菜单底图文字与独立高亮图字形、大小、位置均不同，原生PaintTitle在(62,151/171/192)绘制109×17高亮，导致重影和偏位。图片插件1.2.1在原PaintTitle完成后覆盖菜单区域(0,145,240,67)，以同源精灵在x65、y151/171/192统一绘制选中/灰色未选中状态，加载和设置界面跳过。真实程序集Cecil绑定、原生坐标与状态路径检查已加入构建，完整构建和测试通过。

0.3.2已安装：installations/20260912_160508_014054ec/installation.json。54个补丁文件哈希验证通过，原游戏文件不变。本轮未操作游戏窗口，实机仍由用户验证。

## 0.3.3 原生12px字库与基线

## 0.3.4 菜单残留像素

用户反馈标题菜单字上缘仍有白点。检查菜单精灵和原生PaintTitle/FillRect路径后，改为在插件自有标题纹理中把y145..211菜单区直接写成不透明黑色，并通过PaintTitle前置处理一次绘制清洁标题和三项同源菜单；不再执行原生单高亮后依赖FillRect覆盖。加载/设置界面继续走原逻辑，原始资源不修改。完整构建及菜单区域逐像素边界检查通过，0.3.4已安装，备份installations/20260912_161747_20c64559/installation.json。实机残留是否消除仍待用户验证。

## 0.3.5 设置背景漏译

设置背景图片option.jpg便签的“環境設定”已改为“环境设置”。构建新增scratch1.dat图片来源解析和哈希校验，复用既有LoadGraphic图片替换钩子，未新增adapter。完整构建测试通过，已安装；备份installations/20260912_162559_38f5cb97/installation.json。原游戏资源不变，实机由用户验证。

## 0.3.6 可读运行数据

随包加入runtime.json，与runtime.bin从同一编译记录生成，JSON脚本hash采用十六进制；构建读取JSON转回记录并重新encode_pack，与bin逐字节校验一致后打包。用途及非运行时读取说明同时写入JSON和README。完整构建测试通过。安装预检检测到游戏仍运行，尚未安装0.3.6；最新安装仍以reports/installation_latest.json为准。

0.3.6已按用户要求安装，包含runtime.json；安装文件哈希及原游戏文件不变校验通过。备份：installations/20260912_163453_19fd7184/installation.json。

## 0.4.0 统一系列译文包（当前）

按用户要求沿用 translations.json / translations.bin，采用前作 schema 1、KBZH 字节布局及 engine/core/TranslationPackReader.cs 公共读取器。全语料显示行映射为 scripts 项，颜色/控制保留紧凑target标签，由本作VM适配转换为显示缓存；UI和localization也从同一包读取。原始ruby调查数据留在正式稿/研究材料，不重复装入发行包。JSON 9,204,531字节，BIN 5,114,561字节。与第七作真实encoder逐字节一致性、全语料标签还原和实际运行时离线测试通过。

已删除K8RT0001及旧encoder；用户明确要求不留兼容，安装脚本不包含旧包迁移逻辑。本轮0.4.0安装完成后，直接手动删除游戏插件目录和当前构建目录的runtime.bin/runtime.json，当前目录只保留translations两文件。旧版历史段落描述不代表当前格式。安装记录：installations/20260912_164128_45dd3350/installation.json。未操作游戏窗口，实机由用户验证。
