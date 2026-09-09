# 简体标题图

最终资产：`title.png`，240×100；选定生成原图：`generated.png`。
使用内置 image_gen 编辑，未使用CLI/API fallback。生成后只通过System.Drawing适配游戏要求的尺寸，未再次修改文字或构图。已查看原生尺寸结果，标题为“对交错事件”。

初次提示：

> Use case: text-localization. Edit this game title bitmap for Simplified Chinese. Replace the five title characters 対交錯事件 with exactly 对交错事件. Preserve original 240:100 aspect ratio, horizontal composition, placement of all five glyphs, dark near-black purple background, faint columns of digits, red converging stripe bottom left and gray converging stripe bottom right. Preserve the black second character 交 inside its red block, and other characters in white brush lettering. No added text, subtitles, borders, glow or logos. Keep low-resolution retro game aesthetic. Output only the full rectangular localized title, preferably exactly 240 by 100 pixels; if larger, preserve that exact aspect ratio.

初版仍含繁体“錯”，未采用。最终修正提示：

> Correct ONE character only: third title character is still traditional 錯. Replace it with SIMPLIFIED 错, using 钅 on its left, NEVER 金. Exact full title must be 对交错事件 (Unicode third character U+9519). First 对 is already correct, leave it and remaining characters, background, size, composition, red and gray stripes unchanged. White brush lettering for 错. This is a Simplified Chinese translation. Deliver same full image with this single typo fixed.

替换原资源tuikousaku.res/gif2:0，由公共图片替换构建器计算运行时编号；不修改原游戏资源。原作图像权利归原权利人，此图为汉化衍生资源。
