# 20050817 直接 BIN 变体

第十作离线解析层，以第八作 `gmode-20050817` 为基线。没有复制第八作行解析器，也没有修改其全局表。

已验证的差异：

- `scratch4.dat` 是单字节成员数的偏移表，直接存储 `20050817` BIN；复用 `gmode-v2/vm_frame.py`，不经过第八作 ZIP/FFFF 封装。
- `KOMANDO` 仅读取一个 short；`HAIKEI_SETTI` 仅读取标志及条件文件名。
- 73 为 `SABUTAITORU(byte,string)`；76 为不读操作数的 `SINARIOSENTAKU`。
- 第十作不存在第八作部分列表/图标菜单指令；未知指令严格拒绝。
- 正文、颜色、控制字符及注音行平面继续复用第八作实现。
- 运行时的 `Game`、`Game_adv`、`Game_command` 为普通方法；不能直接使用第八作协程挂钩。运行时尚待实现。

40 份原始脚本（含 4 份容器内备用副本）共 19,834 条指令已完整解析并校验跳转边界。当前只有离线解析能力，不表示中文显示、历史记录或菜单记忆已适配。

运行：`.venv/Scripts/python.exe engine/adapters/gmode-20050817-direct/test_vm.py`。
