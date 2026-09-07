# 第四作接入记录

2026-09-06：本机标题资源和 scn0 确认原题为「白鷺に紅の羽」，暂译《白鹭红羽》。最初完成独立提取和公共构建探针；随后已实现双篇正式运行挂钩并完成7,547条文本初稿和四页中文帮助。当前状态以 [运行层交付记录](RUNTIME_DELIVERY.md) 为准，下文保留最初接入检查结论。

## 配置与边界

- 系列键：kibu4；项目：games/04-shirasagi。
- installation：../../GmodeArchivesPlus_kibu4，相对于系列根目录 series.json。
- 默认作品保持 kibu1；kibu4 的 enabled=false、runtime_tested=false、release_ready=false。
- 新登记 gmode-dual-v1 适配器契约，运行代码待实现。不能直接沿用前三作的 CanvasEx 类型入口。
- 已读取 series/style.md、series/glossary.json，保存第四作独立指导和术语基线。额外继承前作已确认的矢口床子；故意叫错的“知床”须保留。白鹭洲姓氏在本作涉及家族多人，不可自动归并为伊纲。
- 没有修改前三作译文或项目文件，没有安装补丁、启动或操作游戏窗口。

## 引擎差异

Windows AMD64、Mono、Unity 2019.4.9f1，继续采用公共 mono-win-x64-5.4.23.5 构建配置。

第四作 Assembly-CSharp.dll SHA256：6c3b38a4cdd378061ff56945ed3752b56c59cc1226672633d911254d4ca4eee7。

程序集包含 4,083 个方法体、3,559 个字段；前三作各为 4,011、3,219。第四作拆成 appli1.ADV/CanvasEx 与 appli2.ADV/CanvasEx，并新增篇章选择相关流程。原始类型名对照会把命名空间移动算成移除/新增，不能仅据原始变化数量推断核心文本逻辑重写。

以第三作已批准原程序集为基准，只移除 appli1./appli2. 前缀后比较完整规范化方法体（含局部变量与异常处理）：

| 对象 | 方法体一致 | 变化 | 字段声明 |
| --- | --- | --- | --- |
| 前篇 CanvasEx | 53/56 | Play、Paint、静态构造 | 一致 |
| 后篇 CanvasEx | 52/56 | 上述三项及 Adv.MoveNext | 一致 |

Read、Script、ExeText、Jump、构造函数和文字协程保持一致；原生缓冲参数可作为研究基线，中文排版尚未验证。主要差异：

- 前篇加载 sirasagi-1.res（scn0–3）；后篇加载 sirasagi-2.res（scn4–7），后篇 Adv 初始化 Scenario 从 0 改为 4。
- Paint 标题菜单改为“前編をはじめる/後編をはじめる”，菜单宽度倍数 5→7，部分坐标 17→20，菜单初始化 RVA 数据也变化；不能照搬前作标题定位。
- Play 默认声音索引 12→13，静态声音表从 13 项变为 16 项，资源标识为 SHIRASAGI。
- AppliArchive、TitleView、ResourcesManager、ScratchPadManager 与部分 StGraphics 方法也有变化；篇章切换、资源和绘制路由须在正式适配阶段验证。
- 两份 define 与 subscn 内容分别相同；同名 env 内容不同。提取仅在指定 define/subscn 内容一致时合并逻辑文本，另保存所有物理资源的 asset_file/path_id/哈希，后续运行路由不可只凭名称猜测。
- 三作基准对照均显示 SJIS 表和脚本 define 一致。没有据此宣称所有资源兼容。

复现研究：scripts/inspect_assembly.ps1、scripts/compare_engine.py。完整方法及 RVA 差异保存在 research/dual-engine-comparison.json 和 research/dual-engine.diff。

## 原文提取

两份资源包、scn0–7 和 subscn_1–2 已覆盖。19,469 条指令、1,544 个跳转参数通过边界校验，场景非空字符串 7,419 条。连同 localization、Unity 序列化文本及程序集文字，总计 9,963 条记录，其中 7,547 条待译、2,416 条技术/模板候选暂时排除。图片文字和排除候选仍需审查。

work/cache.json 是本作唯一活动译文源，当前正文均未翻译。每条记录保留来源资源、成员和指令位置。重复 extract 已验证 cache 和 manifest 逐字节不变；首次确认题名后仅更新 cache 的 project_name 元数据。重复提取不覆盖译文。

## 公共构建验证

公共 engine/bepinex/build.py 未改动。使用锁定 BepInEx 5.4.23.5 x64 缓存及第四作 Managed 引用，编译 Kibu4Bootstrap.dll；身份 local.kibu4.bootstrap，进程过滤 kibu4.exe。

探针编入 engine/core 的译文包和 gmode-v1 的点阵字体、菜单记忆组件；没有引入前三作 Plugin、特殊地址、帮助图片或译文。入口仅写日志，没有任何翻译挂钩，DialogueReflow 尚未接入。输出位于本作 out/，包名明确为 Kibu4_Bootstrap_NOT_TRANSLATION.zip，最新路径和哈希见 reports/bootstrap_latest.json。

验证通过：本作接入测试 5 项、系列路径测试 5 项、公共构建测试 6 项，以及插件身份、进程过滤、源码编译、完整框架组包和 ZIP 校验。build/verify/install 均实测被 disabled 状态拦截。前三作全部 1,892 个现有文件的哈希保持不变，第四作原游戏目录哈希保持不变。

## 后续工作

先连读全文建立本作新人物、地点和称呼约定，再分场景翻译、审校。正式运行适配须同时覆盖前后篇类型及资源地址，处理篇章选择与切换、独立菜单、图片和帮助页；完成两篇原文指令回放、分页及点击边界检查后生成汉化测试包。实机效果由用户验证。

```powershell
.\run.ps1 paths --game kibu4
.\run.ps1 extract --game kibu4
.\run.ps1 status --game kibu4
.\run.ps1 probe --game kibu4
.venv/Scripts/python.exe games/04-shirasagi/scripts/compare_engine.py
.venv/Scripts/python.exe games/04-shirasagi/scripts/test_onboarding.py
```
