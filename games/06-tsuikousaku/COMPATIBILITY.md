# 第六作接入记录

原题《対交錯事件》，中文题名《对交错事件》。登记安装路径 `../../GmodeArchivesPlus_kibu6`，项目路径 `games/06-tsuikousaku`，均相对系列根目录。`enabled=true`，正式构建与安装已启用；用户实机验证待完成。

## 离线引擎检查

Unity Mono / Windows x64；资源包 `tuikousaku.res`。复用 `gmode-v1`，未新增 adapter，也未修改公共引擎代码。

以第五作已校验原程序集对照，规范化 `appli1.` 命名空间和协程编号后，CanvasEx 56 个方法中 53 个方法体一致（包含局部变量及异常处理），无新增或缺失方法。CanvasEx 字段、嵌入 RVA 数据哈希、SJIS 字符表及指令定义一致。余下差异：

- `.cctor`：游戏／资源名称与音频列表。
- `Play`：默认音频索引 19 → 12。
- `Paint`：图片定位常数 19 → 22、41 → 40。

这些差异不要求分叉文字 adapter；第六作独立挂钩和图片／固定页面策略已实现并通过离线检查。逐项差异、原程序集哈希见 `engine-review.json`。双视角是本作脚本特征，不能仅据此套用第四作双程序集 adapter。已检查18张原生图片，标题经公共图片替换层接入；帮助包含本作特有的第五页。离线一致性不等于实机验收。

## 已完成

提取 scn0–scn11 及两个 subscn，保存原始快照、可定位缓存、指令回放和文件指纹。总条目 11026，待翻译候选 8610，技术／模板排除候选 2416；排除项已按资源与所属方法复核，见 reports/exclusion-review.json；不等同实机可见性验证。当前 8610 条已全部译入，3423 个点击单元完成中日审校。全文状态见 TRANSLATION_COMPLETE.md；点击基线由逐单元审查记录，不由检查器自动批准。

BepInEx 公共层成功编译、组包并校验 `Kibu6Bootstrap.dll`，进程过滤为 `kibu6.exe`；复用公共核心、字体和菜单源码，不依赖前作插件二进制。探针包明确标为 NOT_TRANSLATION，构建报告在 `reports/bootstrap_latest.json`。

提取和探针构建均校验第六作原文件及前五作项目未改变。正式补丁现已安装；没有启动或操作游戏窗口。实机效果由用户验证。

## 复现

在系列根目录运行：

```powershell
.venv/Scripts/python.exe tools/series.py paths --game kibu6
.venv/Scripts/python.exe tools/series.py extract --game kibu6
.venv/Scripts/python.exe games/06-tsuikousaku/scripts/compare_engine.py
.venv/Scripts/python.exe tools/series.py probe --game kibu6
.venv/Scripts/python.exe tools/series.py status --game kibu6
```

后续工作：根据用户的实机反馈修正布局与运行问题。本分支的拼音改编术语属于明确实验覆盖，不提升为系列公共定译。不得复制前作地址、点击基线或布局批准项。

## 正式补丁接入完成（九键拼音实验）

运行时插件Kibu6ZhCN 1.0.0，读取原始脚本后按脚本/指令/槽位替换字符串；IL字符串仅在内存替换。原176个游戏文件安装前后哈希一致，前五作文件未变。五页帮助独立排版，标题240×100替换，旧HTML按钮组件已移除。

离线执行原Read/Jump/ExeText，共22052条指令、1789个跳转参数、8516个脚本文本槽。实际生产换行代码在缓冲区夹具中回放7851段正文，保全44898字符，溢出、丢字、未读滚出均为0。3314个所需字形全部覆盖。以上不等于Unity实机通关。

最新构建与安装分别记录于reports/bepinex_latest.json和reports/installation_latest.json。图片替换也在完整包内，无需另装。后续由用户实机确认。
