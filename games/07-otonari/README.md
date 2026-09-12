# 第七作《林居刑警的搜查笔记》

当前发布版本为1.0.0。用户于2026-09-12完成实机验收并确认汉化完成，授权上传代码和更新已有GitHub Release。开发侧的验证为离线构建、源文件及包校验，未自行启动或操作游戏窗口。

补丁包含中文正文与界面、字体、中文标题、四页帮助、公共图片替换和历史记录插件。标题底部小字为“－小小名侦探－”，正式游戏名保持《林居刑警的搜查笔记》。

## 从源码重建

在系列仓库根目录操作。先按根目录README运行setup.cmd，准备Python依赖、PowerShell 7、.NET SDK及Mono.Cecil；Windows还需.NET Framework 4.x和微软雅黑字体。BepInEx、Unifont由构建脚本下载并校验锁定指纹。

目前提取流程会比对第一、第二作的原始程序集，因此需要安装正版第1、2、7作，并在series.json配置这三作的installation路径。不要只配置第七作后直接构建。现有manifest会核验游戏版本；版本不符时应核查来源，不要删除清单或覆盖译文来跳过检查。

```powershell
.venv/Scripts/python.exe games/07-otonari/scripts/pipeline.py extract
.venv/Scripts/python.exe games/07-otonari/scripts/validate_translation.py
.venv/Scripts/python.exe games/07-otonari/scripts/build_bepinex.py
.venv/Scripts/python.exe tools/package_release.py --game kibu7 --output out/release-kibu7-1.0.0
```

extract从本机游戏恢复被Git忽略的originals、texts与research，包括原始指令回放、颜色命令和固定换行副本；已有cache和manifest须保持逐字节不变。构建复用engine/bepinex、gmode-v1及公共图片和历史记录源码，不需要提交游戏原始资源、程序集转储或下载缓存。

标题替换的正式图源是images/title-zh.png；帮助页根据images/help-pages.translation.json重新排版，并核验本机原始资源。生成中间图与images/source不参与构建。

第七作构建会在本作bepinex/build/history中生成历史插件及附加包，发布工具使用同次构建的产物，无需另行重编前作历史插件。

共享package_release工具检查最新构建报告、译文及源码指纹后，按series/release-names.json的规则生成发布包，并统一用户说明。构建或打包不安装、不启动游戏。工作区安装脚本为scripts/install_bepinex.ps1；安装前退出游戏。

## 维护入口

正式对话译稿为work/dialogue-tagged.json，导入缓存为work/cache.json；修改后应重审受影响的点击与颜色基线。详细审校与历史安装记录见TRANSLATION_STATUS.md，兼容性依据见COMPATIBILITY.md，交接记录见work/TRANSLATION_HANDOFF.md。
