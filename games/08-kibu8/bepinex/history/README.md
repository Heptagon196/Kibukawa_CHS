# 第八作历史记录适配

基于系列 1.6.2，复用 `engine/history/src/HistoryBuffer.cs`、`ColoredHistoryLayout.cs`、`RuntimePolicy.cs`。本目录入口仅用于第八作 20050817 引擎，不修改第一至第七作入口。

构建源为上述共享三份以及本目录身份入口 `HistoryPlugin.cs` 以及 `engine/adapters/gmode-20050817/src/HistoryRuntime.cs`、`HistoryCapture.cs`。引用与公共历史构建层一致；主汉化插件 `local.kibu8.zhcn` 为 BepInEx 硬依赖。最终安装路径必须为 `BepInEx/plugins/KibukawaHistory/KibukawaHistory.dll`。本地已编译 DLL 为 `bepinex/build/history/KibukawaHistory.dll`。

- `BUNSYOU` 仅重置块内记录进度；`DrawAdvString` 的 Priority.Last postfix 仅追加实际绘制过的字符，按行与字符索引去重，重绘不重复。多次点击的后续行在实际绘字前不收录。每块首字符可附当前姓名，经主汉化显示翻译接口取中文。不扫描 Script，不提前读取缓冲片段。
- 各字符颜色从当时 ColorTable 复制成 RGB；之后调色或替换缓冲不会影响历史。物理行以换行保留，同色/变色段均可重新排版。日语 fallback 半宽双字仍对应一个源色槽。
- H / PageUp 开关；L 原为空串或 `---` 时可打开，原有返回功能保留。肩键事件 21 的按下/释放、方向键与摇杆导航复用系列策略。
- 打开时保存并暂停 timeScale、禁用 EventSystem、拦截画布/归档 UI 输入；包装 Run / Game / Game_adv 与嵌套枚举器暂停协程。关闭时恢复原状态，只隔离关闭当帧输入。清空本引擎 Key_* / aKey_* / InputKey 等输入字段。
- 本次会话最近 2000 段；读档后继续追加；退出清空。游戏窗口及真实显示效果仍由用户验证。

离线验证：`bepinex/tests/Run-HistoryTests.ps1` 运行本作缓冲/颜色/空 L 标签测试及共享容量、颜色换行、嵌套暂停测试。共享 RuntimePolicyTests 另已验证导航、关闭输入隔离、肩键边沿和发现去重。使用 Mono.Cecil 只读确认 BUNSYOU/Run/Game/Game_adv/ProcessEvent/KeyFlush 方法签名，未构造游戏对象。

1.6.3：逐字记录已显示内容时，不再把正文物理行尾写入历史；由历史面板按自身宽度换行。保留姓名换行、原生对白块边界、颜色和未显示文本隔离。
