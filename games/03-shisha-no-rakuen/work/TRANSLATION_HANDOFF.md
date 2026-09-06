最新：0.2.2已安装。删除0.2.1两处姓名地址特判，公共DialogueReflow识别整行彩色姓名后的结构换行。三作构建回归通过、译文与术语未改；未启动游戏。详见RUNTIME_DELIVERY.md。

最新：0.2.1已安装，修复scn1老婆婆及scn4伊纲的内嵌姓名换行；仅本作FixedCardLayout结构范围+回归，正文译文不变。详见RUNTIME_DELIVERY.md，实机复验由用户完成。

# 第三作汉化交接

全文初稿及一轮全文交叉审校已完成。唯一活动译文源 work/cache.json：6503条已处理（含7条省略的独立姓名注音），2416条原排除项保持不变。详细状态见 ../TRANSLATION_STATUS.md，审校记录见 ../TRANSLATION_REVIEW.md。

系列规范在 STYLE_GUIDE.md；本作新增术语已锁定于 glossary.locked.json。TERMS_REVIEW.md 是初始审查建议，以锁定表及最终译文为准。神使误读otsukai、遗书mitsukai及解释是必须保留的线索；深森绿（婆婆）与深森京太（男孩）不能混同。两封恐吓信及菜单已统一。

全部12批已check_draft并merge；合并后重复extract及audit通过，原文位置、译文cache、manifest、术语未变。可读译文在translated_texts/，原缓存备份在work/backups/。不得用新草稿覆盖已合并译文而不做冲突检查。

0.2.0正式运行插件及完整包已构建，详见 ../RUNTIME_DELIVERY.md 和 reports/bepinex_latest.json。enabled=true，build/verify/install入口已开放；本次只做安装前CheckOnly，未安装/启动游戏。第三作有独立FixedCardLayout/Plugin/HelpPageView，复用公共层；菜单仅在导出时通过bepinex/menu-labels.json缩短，活动译文不改。后续由用户实机验证，烘焙图片尚未逐一汉化。

约束：不修改前两作译文或既有修改；不操作游戏窗口；实机效果由用户验证。公共构建层和适配器本次未修改，未推送GitHub。
