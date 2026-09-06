# 第三作接入记录

2026-09-06：第3卷《死者乐园》，原题由本机标题资源确认为「死者の楽園」，资源标识 RAKUEN / heaven.res。

## 路径和状态

series.json 登记 kibu3，project 为 games/03-shisha-no-rakuen，installation 为 ../../GmodeArchivesPlus_kibu3；均相对于系列配置。默认作品保持 kibu1。第三作后续已完成正式文本挂钩与离线回放验证，enabled=true；交付状态见 RUNTIME_DELIVERY.md。

已阅读 series/style.md 和 series/glossary.json。独立保存 work/STYLE_GUIDE.md 与 work/glossary.locked.json；系列人物译名作为继承基线，新人物待全文复核。前两作及其已有未提交修改均保留。

## 离线引擎检查

- 三作 Unity 均为 2019.4.9f1；第三作是 Windows AMD64、Mono 后端。
- 第三作 Assembly-CSharp.dll SHA256：6ec1d39ea7e55699c4d6a435b1124593ee8c379301c8ec1e6ef7b3a939636114。
- 对照前两作已批准的原程序集指纹：各有 4,011 个方法体、3,219 个字段；字段声明、SJIS 映射、脚本 define 一致。
- 对第一作变化 4 个方法：Play 默认音效索引 14→12；Paint 中 70→64、140→128、19→17、43→41；Run 协程中的 141/140→129/128；静态构造中的资源标识与声音表变更（15→13 项）。
- 对第二作仅变化 2 个方法：Paint 一处图像横坐标 21→17；静态构造中 KAIROU/kairou.res→RAKUEN/heaven.res，se_msg1→se_msg、se_noise→se_phone、se_phone→se_tel。
- CanvasEx 构造、Read、Script、文字协程、ExeText、Jump 及字体菜单相关方法体未变。因此 gmode-v1 可作为后续复用基础；尚未验证第三作专属界面、地址区间与中文排版。规范化方法体一致不代表所有资源或静态 RVA 数据一致。

## 文本与构建

提取 scn0–scn10 和 subscn_1–2：16,991 条指令、885 个跳转参数通过边界检查，6,409 个场景非空字符串。加上 localization、Unity 序列化文本及程序集文字，共 8,919 条记录，其中 6,503 条待译、2,416 条技术/模板候选暂时排除。后续已完成6,503条记录初稿及一轮全文交叉审校，详见 TRANSLATION_STATUS.md。图片文字及排除候选仍需人工复核。

公共 engine/bepinex/build.py 未改动，复用锁定的 BepInEx 5.4.23.5 x64 缓存与构建流程，以第三作 Managed 引用编译 Kibu3Bootstrap.dll。身份 local.kibu3.bootstrap，进程过滤 kibu3.exe。公共译文包、点阵字体及菜单组件已编译；入口仅记录日志，没有安装翻译挂钩。未复制前作 Plugin、聊天/名单地址或图片。DialogueReflow 待第三作策略确认后接入。

验证包位于本作 out/，以 NOT_TRANSLATION 标识，具体路径与哈希见 reports/bootstrap_latest.json。这是构建验证产物，不是实机汉化测试包。

## 验证结果

- 系列路径测试 5 项、公共构建测试 6 项通过。
- 第三作插件身份、进程过滤、公共源码编译、完整框架打包和 ZIP 校验通过。
- 重复 extract 成功，已有 cache 和 manifest 逐字节保持不变。
- build、verify、install 均实测被待审状态拦截。
- 前两作项目全目录（包括未跟踪文件）1,482 个文件哈希保持不变；第三作游戏目录提取和构建前后哈希不变。
- 未安装补丁、未启动或操作游戏窗口。runtime_tested=false，release_ready=false，实机由用户验证。

## 接入阶段后续（已完成情况见 RUNTIME_DELIVERY.md）

文本与术语初稿已完成并审校。下一步建立第三作专属运行入口、原文地址匹配与特殊页面策略，完成真实指令回放、点击边界及重排检查，生成正式测试包交给用户验证。任何公共层修改都需对启用作品做构建回归，不能修改旧译文。

命令：

```powershell
.\run.ps1 paths --game kibu3
.\run.ps1 status --game kibu3
.\run.ps1 extract --game kibu3
.\run.ps1 probe --game kibu3
```
