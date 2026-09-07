# 第四作《白鹭红羽》0.3.0 交付记录

前后篇翻译已完成，2026-09-08追加到现有Release：
https://github.com/Heptagon196/Kibukawa_CHS/releases/tag/chs-01-03-2026.09.07

下载名：Kibukawa-04-Shirasagi-CHS.zip。中文显示名：癸生川凌介 04-白鹭红羽-CHS.zip。SHA256：6ec0ee1c9635b33a300e5169bf68ddf194af50c488d63c8f696789eba20cba34。

## 实现

分别挂钩appli1.CanvasEx与appli2.CanvasEx，复用公共BepInEx构建与gmode-v1运行层。双篇脚本按原始地址替换，不写回原剧情资源、程序集或存档。包含中文字体与四页帮助。

已修正确认的对白引号与多余空格；结尾紫色姓名由正文指令显示，校验禁止误加后引号。开场scn0地址15365–18282整段制作名单演出沿用原作定时、折行、清屏及点击等待，不额外插入重排分页。18284起恢复普通对白重排。两句演出译文已缩短以适配原版行宽。

## 验证

发布构建通过7,419个脚本文字槽、19,546次原程序集Read、76,070条双篇断言；6,869条正文命令回放，42,039字符守恒，19,517条排版断言通过。系列打包工具核对源码、译文、ZIP及包内哈希；上传后与GitHub资产摘要一致。

用户负责实机效果验证；不宣称覆盖全部视觉与分支。仍有9项引号边界和4处独白缩进保留未定，刻意排版留白保留。部分标题美术及烘焙图片仍为原文。

## 从源码构建

配置series.json中的第四作安装路径，运行setup.cmd准备依赖。然后执行：

```powershell
.\run.ps1 extract --game kibu4
.\run.ps1 build --game kibu4
.\run.ps1 install --game kibu4 -CheckOnly
```

extract从对应正版游戏重建本机派生文件，并校验已有缓存与manifest不变。构建不安装、不启动游戏。
