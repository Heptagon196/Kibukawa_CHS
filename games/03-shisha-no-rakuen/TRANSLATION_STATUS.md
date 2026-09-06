# 第三作《死者乐园》文本进度

2026-09-06：全文初稿及一轮全文交叉审校完成，已合并到唯一活动译文源 `work/cache.json`。未安装补丁、未操作游戏窗口、未推送 GitHub。

## 完成范围

- 6,503 条可翻译记录全部处理：6,496 条非空译文，7 条独立姓名注音按系列规范省略；这些空译的原文已登记在 project.json。
- 11 个场景批次 scn0–scn10，共 6,389 条；由子 agent 独立翻译、自审，再由其他 agent 全文对照交叉审校。
- 姓名栏、存档和界面合并为 ui 批次，共 114 条，由主控翻译并验证。
- 2,416 条原本排除的技术/模板候选保持 status=7、空译，没有作为已翻译内容凑数。
- 原始状态为 translation_status=1（初稿），没有宣称最终定稿或实机通过。

## 术语与线索

已在本作 glossary.locked.json 增补角色与设施，不修改系列基线或前两作。锁定神之过山车、末日决战、亚马逊漂流、洛奇／洛克鸟、控制室／系统管理室、侧台／栅顶／横梁等区别。深森绿与深森京太是不同人物；冒名与误认仍保留原文揭示时机。

“神使”的误读、遗书假名写法和后文解释已跨章协调；必要译注置于对白引号之外，并保留 otsukai／mitsukai 的差异。两封恐吓信的各次复现逐条一致。完整审校修正记录见 TRANSLATION_REVIEW.md（含剧透）。

## 验证

12 个批次均通过 ID、源文位置、占位符、无假名残留、脚本控制字符和 UTF-16 缓冲长度检查。最长脚本文本17个UTF-16单元，低于当前检查上限20。

合并后重复 extract，cache、manifest、术语快照哈希全部保持一致；完整 audit 通过，原文和定位不变，可读译文导出与cache一致，前两作项目及第三作原游戏未改变。

译文 SHA256：581080c3d946244ffed1356ebcca91b9c43d72c638acc411345e51f0a48954ba

## 下一步

第三作0.2.0正式运行插件已构建并离线验证，详见 RUNTIME_DELIVERY.md。enabled=true、release_ready=true，runtime_tested=false。已接入字体、菜单短名、四页帮助、固定卡片及真实指令回放；未安装或操作游戏。

标题美术及其他烘焙图片、Unity实机场景与实际视觉效果仍待后续检查，实机由用户验证。

## 文件与命令

活动译文：work/cache.json；可读文本：translated_texts/；术语：work/glossary.locked.json；验证：reports/translation-audit.json。原缓存备份在 work/backups/。

```powershell
.\run.ps1 status --game kibu3
.venv/Scripts/python.exe games/03-shisha-no-rakuen/scripts/translation_batches.py audit
```

本机批次、草稿与审校报告保留在 work/batches、work/drafts、work/reviews（沿用仓库忽略规则）。最终译文源、术语、状态文档与本文件保留在仓库项目内。
