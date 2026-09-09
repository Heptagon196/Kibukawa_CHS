# 第六作：带颜色与指令边界的翻译流程

本作的对话翻译入口为 `work/dialogue-tagged.json`。原来的纯文本分摊脚本已禁用。缓存中的单条文本是运行时产物，不再作为跨段翻译的入口。

例如开场介绍的译稿保留了：

```text
这次的故事，将从我<boundary=6856/><color=GREEN>生王正生</color><boundary=6857/>和<boundary=6858/><color=RED>白鹭洲伊纲</color><boundary=6860/><boundary=6861/><color=YELLOW>两个视角</color><boundary=6862/>展开。
```

颜色标签来自原始 opcode 80/81：YELLOW=2、RED=5、GREEN=6；其他值保留原始数字。`boundary` 是不允许跨越的原始执行区间边界，标识其后第一个文本槽位。它不仅保护颜色切换，也保护动态数字等执行指令。空区间允许存在，不添加填充文字，也不删除游戏指令。标签不会显示在游戏中。

## 操作

在系列仓库根目录执行：

```powershell
.venv/Scripts/python.exe games/06-tsuikousaku/scripts/pipeline.py extract
.venv/Scripts/python.exe games/06-tsuikousaku/scripts/tagged_dialogue.py check
```

提取会写入 `texts/dialogue-tagged.json`，同时保留已有翻译缓存和正式译稿。要另存当前带标签材料：

```powershell
.venv/Scripts/python.exe games/06-tsuikousaku/scripts/tagged_dialogue.py extract --output work/dialogue-preview.json
```

编辑正式译稿中每个单元的 `target`；保留 `source`、地址、所有标签及顺序。然后导入：

```powershell
.venv/Scripts/python.exe games/06-tsuikousaku/scripts/tagged_dialogue.py import
.venv/Scripts/python.exe games/06-tsuikousaku/scripts/validate_translation.py
.venv/Scripts/python.exe games/06-tsuikousaku/scripts/build_bepinex.py
```

导入只在同一个颜色和执行区间内部拆分文字。无法容纳、缺少标签、重复标签、错序或新增标签都会报错。空槽位记录原文和原因。导入不自动更新整句与着色复核基线；改变整句或强调词后，必须人工复核相应基线。程序保证结构一致，强调对象是否准确仍需要译者判断。

`research/color-spans.reviewed.json` 保存 409 处着色段的原文、颜色、地址及复核后的中文。构建从原游戏重新解析指令，对照正式带标签译稿、着色基线和点击单元基线进行校验，不能通过直接修改缓存绕过标签检查。

## 本次修复

修复按纯文本长度分摊造成的跨色段错位。保留原始字节码、跳转地址、颜色指令和动态数字位置；对少数无法沿原始颜色顺序表达的句子调整语序，并把拼音方案中遗漏的“两位数”改为“两位或三位数”。未改动前作译文或公共 adapter。

验证范围：3423 个点击单元、409 处着色段、标签损坏拒绝、动态边界保护、容量限制、谜题逻辑和离线运行时回放。实际游戏画面由用户验证。
邮件固定排版：research/hard-breaks.json 登记原始 opcode 77 的硬换行位置。公共标签模块输出 <br=后续槽位编号/>，导入时禁止删除或跨越。第六作开场邮件保留八行，由 test_email_layout.py 验证实际重排回放结果。
