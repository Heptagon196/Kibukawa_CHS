# 系列带标签对话流程

适用于第一至第六作。公共实现位于 `tools/dialogue_tags.py`，各作只保留提取器、原始脚本路由和构建配置。未增加新的 adapter，也未改动原游戏字节码。

正式对话译稿：每作 `work/dialogue-tagged.json`。每个点击单元保留原文 `source` 和译文 `target`，用 `<color=RED>文本</color>` 等标签标明原始颜色；`<boundary=条目ID/>` 保留颜色或执行指令区间边界，尤其不能跨越动态数字。标签仅供翻译、校验和导入，不会显示在游戏中。

## 提取、修改、检查

```powershell
./run.ps1 extract --game kibu2
./run.ps1 tag-extract --game kibu2
./run.ps1 tag-check --game kibu2
```

提取结果写入本作 `texts/dialogue-tagged.json`；已有正式译稿和译文缓存不会被覆盖。首次翻译可以从提取材料建立正式译稿。日常编辑正式译稿的 `target`，保留所有结构标签和 `source`，然后执行：

```powershell
./run.ps1 tag-import --game kibu2
./run.ps1 tag-check --game kibu2
./run.ps1 click-check --game kibu2 --strict
./run.ps1 build --game kibu2
```

导入只能在同一颜色、同一执行区间内分配文本，不能按整句长度跨段分摊。没有足够空间或标签损坏时立即报错。未变的区间保持已有槽位分配。必要空槽记录原文及原因，空字符串不能替换为控制用的 null。

`tag-check` 对照正式译稿与实际缓存，并核对 `research/color-spans.reviewed.json`。整句复核基线仍为 `work/click_boundaries.reviewed.json`。修改强调词或整句后，需逐处人工复核对应基线；导入不会自动批准任何基线。结构检查不能代替翻译语义判断。

所有六作的 BepInEx 构建均从原文件重新解析指令，再强制执行公共标签和着色语义检查。直接修改缓存或从旧纯文本流程导入，不能绕过构建检查。

## 本次前五作迁移

|作品|点击单元|着色段|修改文本槽|调整全文的单元|
|---|---:|---:|---:|---:|
|第一作|2684|205|62|5|
|第二作|3312|333|174|7|
|第三作|2679|273|336|15|
|第四作|3055|224|240|9|
|第五作|2560|103|87|5|

逐处复核了全部 1138 个着色段。修改集中于颜色对应词语的分段；数字表格、聊天昵称、整段书信等原本正确的着色保留。确实无法按原颜色顺序表达时才调整语序。每作 `work/color-migration.reviewed.json` 记录逐槽和逐句的原文、修改前后文本，便于追溯。

第六作复用公共实现；本次前五作迁移不修改第六作译文。另一个任务的固定换行修复保留。六作共 17713 个点击单元、1547 个着色段。

回归检查：

```powershell
.venv/Scripts/python.exe tools/test_dialogue_tags.py
```

包含首次构建前的提取、六作完整标签往返、错误标签与动态边界拒绝、容量限制、原第二作错位回归、错误缓存重新导出后仍被着色基线拦截、无效导入不写缓存、未改译稿导入不改槽位。各作另运行已有原始引擎及排版回放。实机画面由用户验证。
