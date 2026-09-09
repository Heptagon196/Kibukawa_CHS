# 第六作本地化交接

全作提取文本已完成：8,610/8,610 条，待译 0；3,423 个点击单元完成中日审校。活动文件为 `work/cache.json`。完整状态、特殊文本规则、复核命令及尚未完成的补丁工程见 `../TRANSLATION_COMPLETE.md`。

不要重新开始翻译 scn2，也不要把旧的 opening-localization 报告当作最新进度。当前证据为 `reports/full-text-validation.json`、`work/click_boundaries.reviewed.json`、`reports/exclusion-review.json`。中日全文在 `translated_texts/full-review.md`。

先前的首批译文保持不变；本次完成 scn2–scn11、subscn 和系统文本，并复核特殊槽位。公共术语及本作术语已经归并，后续修改需同步对应来源哈希。每次仍应同时读取系列规则及本作锁定表。

下一阶段是正式翻译挂钩、中文字库、图片文字、中文布局与汉化打包。仍复用 gmode-v1 和公共 BepInEx 构建层，不新增 adapter，不复制前作地址或布局审批。当前探针 NOT_TRANSLATION。禁止自动更新点击已审基线来绕过审校。

用户要求前作译文不动，不操作游戏窗口；实机由用户验证。未安装补丁、未提交或推送 GitHub。
