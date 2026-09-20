# Harmony 启动中断与选项卡死修复

- 主插件版本：0.1.16
- 实机症状：0.1.15 启动后主汉化不生效，点击选项卡死。
- 日志证据：`BepInEx/LogOutput.log` 在载入主插件时反复记录 `Unexpected direct typewriter catch loop count: 0`，随后没有出现主插件完成初始化的记录。
- 根因：0.1.14 新增的 `Game_adv` 逐字恢复 transpiler 误以为原版永久自循环的目标标签挂在前一条 `pop` 上。真实 Harmony 指令把该标签挂在自跳转的 `br` 指令自身；与选项记忆 transpiler 组合后，错误匹配令 Harmony 中断主插件安装，翻译和选项挂钩都未完整生效。
- 修复：只匹配 `pop; br self; ldc.i4.1; ret` 的真实自循环，其中 `br` 自身持有其目标标签；仍要求全方法恰好匹配一次，未知程序集形状继续拒绝修改。
- 防回归：新增 `Run-HarmonyPatchCompositionTests.ps1`，从 SHA256 锁定的原版 `Assembly-CSharp.dll` 读取真实 `Game_adv` 指令，初始化真实字段，依次运行选项记忆与逐字恢复 transpiler，并从原版 IL 重放两遍以模拟 Harmony 后续插件重建。0.1.15 稳定复现同一 `count: 0`，0.1.16 两遍通过。
- 完整校验：`verify --game kibu10` 通过；真实 40 个 BIN、8,907 个显示块、943 个字符串以及 UI、图片、历史、选项记忆、真实 IL 组合测试全部通过。
- 正式包：`out/CHS_20260921_024227_526388300/Kibu10_CHS.zip`
- SHA256：`a774ff9156662a6ec45a10f6cd1b6ea55cc40e94f574bd452f974afa940664ba`
- 安装记录：`installations/20260921_024243`
- 安装后主插件 DLL SHA256：`a386113179dc0f85010dee332b95fa890e1fce92d4bf52df7f285bcb5bfe7974`
- 安装结果：102 个补丁文件核对完成；原游戏与存档文件未改变；未启动或操作游戏窗口。新实机启动日志需由用户下次运行后生成。
