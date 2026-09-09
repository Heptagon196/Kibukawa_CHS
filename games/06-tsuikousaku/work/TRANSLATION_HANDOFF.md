# 第六作本地化交接

当前为九键拼音实验分支 `experiment/kibu6-pinyin-puzzle`，原方案保存于提交 `550918d`。全作提取文本8,610条，活动文件为 `work/cache.json`；3,423个点击单元中，本次明确审查137个变化单元。方案、算术与限制见 `../PINYIN_EXPERIMENT.md`。

不要重新开始翻译 scn2，也不要把旧的 opening-localization 报告当作最新进度。当前证据为 `reports/full-text-validation.json`、`work/click_boundaries.reviewed.json`、`reports/exclusion-review.json`。中日全文在 `translated_texts/full-review.md`。

用户授权本分支改写第六作数字、化名及关联提示：200→163→144→96→67→25→0；西野优美子替代滨川优美子，XIYE与YUAN均为25；开场9822→YUBA→鱼吧。原日文与跳转地址不变，调整部分选项显示顺序。已移除所有译注；公共表维持检查点原方案，本作表显式记录实验覆盖，不能将实验译法提升为系列定译。旧work/drafts与此前日文参考组件不适用于本分支，不得重新套用覆盖当前缓存。

下一阶段是正式翻译挂钩、中文字库、图片文字、中文布局与汉化打包。仍复用 gmode-v1 和公共 BepInEx 构建层，不新增 adapter，不复制前作地址或布局审批。当前探针 NOT_TRANSLATION。禁止自动更新点击已审基线来绕过审校。

用户要求前作译文不动，不操作游戏窗口；实机由用户验证。未安装补丁或推送GitHub。复核命令：`scripts/test_pinyin_puzzle.py` 与 `scripts/validate_translation.py`（工作区虚拟环境Python）。
