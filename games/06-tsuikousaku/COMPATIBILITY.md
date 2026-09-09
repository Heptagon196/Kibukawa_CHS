# 第六作接入记录

原题《対交錯事件》，中文题名《对交错事件》。登记安装路径 `../../GmodeArchivesPlus_kibu6`，项目路径 `games/06-tsuikousaku`，均相对系列根目录。`enabled=false`，正式构建与安装仍关闭。

## 离线引擎检查

Unity Mono / Windows x64；资源包 `tuikousaku.res`。复用 `gmode-v1`，未新增 adapter，也未修改公共引擎代码。

以第五作已校验原程序集对照，规范化 `appli1.` 命名空间和协程编号后，CanvasEx 56 个方法中 53 个方法体一致（包含局部变量及异常处理），无新增或缺失方法。CanvasEx 字段、嵌入 RVA 数据哈希、SJIS 字符表及指令定义一致。余下差异：

- `.cctor`：游戏／资源名称与音频列表。
- `Play`：默认音频索引 19 → 12。
- `Paint`：图片定位常数 19 → 22、41 → 40。

这些差异不要求分叉文字 adapter；第六作独立挂钩和图片／固定页面策略仍须实现与检查。逐项差异、原程序集哈希见 `engine-review.json`。双视角是本作脚本特征，不能仅据此套用第四作双程序集 adapter。图片资源覆盖范围尚未审查，离线一致性不等于实机兼容承诺。

## 已完成

提取 scn0–scn11 及两个 subscn，保存原始快照、可定位缓存、指令回放和文件指纹。总条目 11026，待翻译候选 8610，技术／模板排除候选 2416；排除项已按资源与所属方法复核，见 reports/exclusion-review.json；不等同实机可见性验证。当前 8610 条已全部译入，3423 个点击单元完成中日审校。全文状态见 TRANSLATION_COMPLETE.md；点击基线由逐单元审查记录，不由检查器自动批准。

BepInEx 公共层成功编译、组包并校验 `Kibu6Bootstrap.dll`，进程过滤为 `kibu6.exe`；复用公共核心、字体和菜单源码，不依赖前作插件二进制。探针包明确标为 NOT_TRANSLATION，构建报告在 `reports/bootstrap_latest.json`。

提取和探针构建均校验第六作原文件及前五作项目未改变。没有安装补丁、启动或操作游戏窗口。实机效果由用户验证。

## 复现

在系列根目录运行：

```powershell
.venv/Scripts/python.exe tools/series.py paths --game kibu6
.venv/Scripts/python.exe tools/series.py extract --game kibu6
.venv/Scripts/python.exe games/06-tsuikousaku/scripts/compare_engine.py
.venv/Scripts/python.exe tools/series.py probe --game kibu6
.venv/Scripts/python.exe tools/series.py status --game kibu6
```

继续工作：全文翻译及术语归并已完成；实现本作正式挂钩、字库、图片和中文布局，完成离线验证后再启用正式构建。不得复制前作地址、点击基线或布局批准项。公共术语表按语境复用，确认的新术语在本作审校完成后归并。
