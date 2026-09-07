# 第四作汉化接续说明

当前0.3.0已完成7547条选定文本初稿及对照审校，2416条技术/模板候选仍排除；四页包装层帮助已按本作原图译成中文。下一步主要是用户实机验证与反馈修订，烘焙图片仍未逐一汉化。

唯一活动源为work/cache.json。work/drafts/scn0–scn7.json与ui.json是经主控审校后的稿件来源，不能再运行旧builder覆盖它们（builder只是翻译过程草稿）。更改应同步对应draft并验证，严禁自动重新应用全部初稿覆盖后续修订。

本作术语见work/glossary.locked.json。新增鸟喙山（正式名九之桥山）、大凤制药集团、白鹭集团、户籍副本等。伊纲与饭纲使必须区分；过去与现在的姓氏和冒名身份按原文时机处理，不能根据最终身份改写早期称呼。

原文索引3861为独立姓名注音尾，批准空译记录在project.json。其余选定条目均已翻译。菜单运行短名在bepinex/menu-labels.json，正文保留完整语义。

双篇运行适配器gmode-dual-v1分别处理appli1.CanvasEx/scn0–3与appli2.CanvasEx/scn4–7；公共subscn两份物理来源已一致性校验。正式构建运行全部离线测试；不操作游戏窗口。实机效果由用户验证。

已观察到其它任务修改第三作代码与安装产物，应保留这些工作；前三作译文及术语与基线一致。详见RUNTIME_DELIVERY.md与TRANSLATION_STATUS.md。
