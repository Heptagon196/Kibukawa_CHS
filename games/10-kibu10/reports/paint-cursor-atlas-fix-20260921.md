# 0.1.18：绘制游标与全屏字库修复

0.1.17 实机反馈：全屏中文字形重叠，初始化数据确认框仍停滞。此前“逐行等长即可避免卡死”的判断不成立。

## 证据和复现

- BepInEx 日志已包含 `Chinese runtime ready`，本轮不再是加载失败。
- `C:/Users/hepta/AppData/LocalLow/G-MODE/kibu10/Player.log` 记录 `IndexOutOfRangeException`，发生于 `CanvasEx.PaintADV_text` 的 `[0x00400]`。原始程序集该位置对应 `bg_itigyougun_mojiretu[PrintDanYoyaku][PrintMojiKetaYoyaku]` 字符读取。
- 新增 `NativeFrameReplay.cs` 执行 SHA256 锁定程序集提取的原始 `Game_adv`、`PaintADV_text` 指令，接入生产显示挂钩；图形和音效使用替身，不启动游戏或读写存档。
- 初次回放错误地采用绘制先行，未复现；按原生 `Game()` 先更新、再由 `Idle()` 绘制的顺序回放，未修复版本稳定抛出 `Index was outside the bounds of the array`。发布测试现在保留这一调用顺序。
- `Game_adv` 先推进请求游标，原生增量绘制仅把完成游标加一；首帧落差或完整重绘未提交游标时，落差持续到行尾。只比较行数、字符数和控制数组的旧测试不能覆盖此状态问题。
- 全屏测宽和定位使用 12px 网格，绘制作用域却强制使用 16px 正文字库，导致字形交叠。新增测试在实际绘制作用域内检查所选字库。

## 修正和验证

- 待绘制字符领先完成字符超过一个时，使用原生重绘分支公开到当前请求位置；成功绘制后提交完成行、格与字符游标。未修改 `Game_adv` 异常路径，未增加或消费点击控制码。
- 全屏 12px 网格使用 12px 字库；普通正文和姓名栏维持 16px；其他文字字号规则不变。
- 六组原始指令回放全部到达原生确认等待：三种垂直模式，各覆盖直接更新及首次重绘。
- `run.ps1 verify --game kibu10` 全部通过，包括 40 个真实 BIN、8,907 个显示块、943 个字符串及现有 UI、排版、图片、选项与历史检查。
- 回放验证的是到达等待事件，不能替代 Unity 实机视觉和确认/取消交互验证；项目仍保留 `runtime_tested=false`。

## 交付

- 包：`out/CHS_20260921_030827_155885900/Kibu10_CHS.zip`
- 包 SHA256：`e11ea83581c45192e424b1269ad7c9ab6ded8fe961c1bf8cac35ffeabd7f750a`
- 安装：`installations/20260921_030847`，102 个文件，原游戏及存档未变，未操作游戏窗口。
- 已安装 DLL 与包一致，SHA256：`0e1016ef2d913ddba379e34acff0fbdd85f5635bf06838d9f6625d86748ded1b`。
