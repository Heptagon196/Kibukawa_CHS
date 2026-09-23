# 癸生川网页番外汉化

本目录与 Steam 游戏补丁独立。原作公开入口及引擎记录见 `sources.json`。

## 当前进度（2026-09-23）

| 作品 | 文本 | 运行验证 | 未完成事项 |
| --- | --- | --- | --- |
| 诞生纪念日事件 | 802 条文本行已译，含普通与兼容脚本；去重后 418 条，标题图及系统提示已汉化 | 中文标题、开场、记录及存读档界面已验证，页面脚本错误为 0 | 所有分支逐一通关尚未完成 |
| 运行测试事件Ⅱ（原名：動作確認事件Ⅱ） | 305 条正文、65 项菜单及标题图已译；谜题变量统一为“运行＋测试” | 已显示中文菜单与开场三行；正文静态宽度检查通过；中文字体无缺字 | 所有分支逐一通关尚未完成；Pyxel 启动提示为运行器自身界面 |
| 狭稻温泉乡杀人事件（原作未完成版） | 2162 条文本行、146 项界面文本及标题图已汉化 | 五章入口、三行对白及叙述、存档写入与读取列表已验证；章节入口加载错误为 0 | 原作正式流程只有四章；第五章为未完成草稿，未补写结局 |

这是本地汉化构建，尚未逐一通关所有分支。三部作品已核对翻页、等待和插值变量标签，未发现标签丢失。中文独立存档标识避免覆盖原版进度。

## 本机预览

双击 `start.cmd`，保留服务窗口，在浏览器打开 `http://127.0.0.1:8766/`。只监听本机。关闭窗口或按 Ctrl+C 停止服务。端口被占用时，可执行 `python serve.py --port 8767`。

Pyxel、Pyodide、WASM 与字库均使用经过 SHA-256 校验的本地固定版本，游玩时无需联网。生日篇使用本机中文字体；三部标题图均已汉化。

## 下载、构建与校验

在 `translation_workspace` 下运行：

```powershell
.\.venv\Scripts\python.exe web/fetch_sources.py
.\.venv\Scripts\python.exe web/fetch_pyxel_runtime.py
.\.venv\Scripts\python.exe web/verify.py
.\.venv\Scripts\python.exe web/build_birthday.py
.\.venv\Scripts\python.exe web/build_operation.py
.\.venv\Scripts\python.exe web/build_saina.py
node web/test_flash.cjs
node web/test_saina_chapters.cjs
node web/test_saina_ui.cjs
node web/test_web_games.cjs
.\.venv\Scripts\python.exe web/check_saina_layout.py
```

`originals/` 为作者站点的原始资源，`work/dialogue.json` 为带原文、定位、译文的文本表，`build/` 为本机构建候选包。原作程序和图片不纳入 Git。`source-manifest.json` 记录下载文件 SHA-256 及失败项；失败项包括未使用或原站本来就缺失的资源，不等于全部影响主流程。

Pyxel 字库使用前十作已校验的 GNU Unifont 16.0.04 本地缓存。构建脚本保留原游戏逻辑，只替换显示文本、字体和中文存档标识，并关闭原程序在 VSCode 环境中自动用日文源脚本覆盖已编译文本的开发功能。

## 温泉篇调查记录

- 作者公开入口：`https://ikrm.secret.jp/saina/`，入口 `start.htm` 加载 `LemoNovel.swf`。
- `LemoNovel.ini` 指定 `script/first.adv` 和 `script/def_macro.adv`。已取得 `s01.adv` 至 `s05.adv`。第五章开头原有 `TO BE CONTINUED` 和退出指令，正式流程实际止于第四章。
- `s06.adv`、`s07.adv` 返回 404；必须保留原作未完成的边界，不补写结局。
- 已移除未使用的 `kom.swf` 预载和被表情立绘取代的 `izuna.swf` 初始加载；纠正 `se_newward.mp3` 拼写，黑背景复用原作已有 `Effect/black.jpg`。
- Ruffle 0.6.0 与 nightly-2026-09-23 都复现过菜单不可见。单纯更换运行器或字体不足以解决。
- 用开源 [JPEXS](https://github.com/jindrapetrik/jpexs-decompiler) 导出按钮脚本后，通过运行时测量确认：Ruffle 延迟计算 TextField 自动尺寸，旧引擎在布局计算完成前关闭 `autoSize`，留下错误高度。诊断日志读取尺寸时会意外掩盖问题，因此用无日志版本重新验证。
- `patch_saina_flash.py` 仅在 `ChgCaptionWidth` 关闭自动尺寸前读取正文及阴影的宽高，强制完成测量；保留原作菜单 32px 字号。补丁通过 JPEXS 在构建副本内应用，未改原始 SWF。
- 最终使用 [Ruffle](https://github.com/ruffle-rs/ruffle) 的 Canvas 字体后端和随包 [Noto Sans SC](https://github.com/google/fonts/tree/main/ofl/notosanssc)（OFL）。等待常规、粗体字体加载后才启动游戏。运行器、字体、构建用 JPEXS 和 Temurin JRE 均有固定 URL 和 SHA-256；见 `flash-dependencies.json`。JRE 与 JPEXS 不进入游戏构建包。
- 原脚本定义 `SVersion`，却读取未定义的 `version`；构建时统一定义为 `version`，标题版本恢复 `0.126`。本地存档使用独立 ID。
- `test_flash.cjs` 在独立浏览器验证菜单文字像素、点击开始及第一章请求，截图与日志保存在 `reports/`。不是全流程通过证明。可通过 `PLAYWRIGHT_PATH` 和 `BROWSER_PATH` 指定本机工具位置。
- 回归对照：`node web/test_flash.cjs --original` 仅将 SWF 换回原版，其余配置相同，结果为 0 个文字像素、退出码 1；修复版为 2550 个文字像素、第一章已加载、退出码 0。`--extended` 可继续推进第一章并截图。JPEXS 日志与反编译的原作代码仅保存在忽略的 `reports/` 内。
- `make_flash_font.py` 保留为 GNU Unifont 字库实验，不参与最终构建。
- `localize_saina_ui.py` 只替换可见字段，保留日文跳转标签、人物内部 ID 和资源键；存档场景说明另行汉化。
- Noto 字体的实际行框高于原字体，因此正文保持 27px，额外行距由 16 改为 2；三行对白及三行叙述均已截图确认完整显示。存档四行按钮单独使用 24px，返回按钮改为中文文字。
- `repair_saina_draft.py` 保留正式流程结束的说明，玩家可自行选择阅读附带的第五章草稿。修正草稿中工作／恋爱两个话题的重复标签与错配变量；为原稿末尾叙述补充翻页，未写出的“关于我”分支显示汉化说明。没有添加虚构事件。
- 原稿旅馆翻新时间存在“五年前／三年前”的不一致，按原文保留，未擅自统一。
- `check_saina_layout.py` 用随包字体检查剧情固定行宽与普通页面的三行上限；结果为 0 项。实际浏览器排版截图是补充检查，不能以静态检查替代。
- 标题素材由内置 image_gen 编辑并人工核对，原资源保留。最终提示词及保存位置见 `artwork-prompts.md`。
- 生日篇补齐变量引用的三种说话音效；原资源收集器已加入动态声音引用识别。记录／存读档 HTML 使用本地中文模板。

## 翻译说明与后续审校

- 生日篇的「冷やかし／暖かし」暂处理为“泼冷水／送温暖”，保留披肩礼物的呼应。
- 「煮て／似て」「蒸し返す」和「ストレート」包含双关，目前用自然中文表达情境，需在最终审校时决定是否加译注。
- 正文中的日文振假名不原样附在中文汉字上；姓名读音笑话保留罗马音。
- 标题译名暂定，不代表统一术语已锁定；原始标题保存在 `sources.json`。

未修改 Steam 安装、存档或已有 GitHub Release。
