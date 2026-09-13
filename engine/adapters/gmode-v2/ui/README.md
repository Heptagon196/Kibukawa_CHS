# Unity UI 显示本地化公共层

`src/UiLocalizationRuntime.cs` 提供 BepInEx/Harmony 下的显示本地化机制，不解析剧情脚本，不写入存档，不包含作品译文。

## 职责与调用

作品提供一个很薄的派生类，在 `Initialize` 前设置：

| 配置 | 用途 |
| --- | --- |
| `Owner` | 本作品 UI Harmony ID，用于独立卸载挂钩 |
| `Exact` / `Keys` | 整段显示字符串表 / 本地化 key 表 |
| `IsExcluded` | 不应翻译的技术标记判断 |
| `TranslateSpecial` | 整串查表未命中时的作品专用格式处理 |
| `FontNames` | 系统字体候选列表 |

从插件 `Awake` 调用 `Initialize(logger)`，每帧调用 `Update()`，销毁时调用 `Dispose()`。可用 `RegisterDisplayTranslation(source, target)` 注册场景提供的整段姓名等文案；冲突译文和技术标记会被拒绝。`TranslateDisplay` 可供历史姓名显示复用。

公共实现负责：

- Unity `Text.text` / `OnEnable`、Steezy `Localization.Get` 与 Socotra `DrawString` / `DrawChars` 挂钩。
- 整串替换；不对字符串中的任意子串翻译，不修改原脚本缓冲。
- 输入框内容保护、中文字体选择、原字号及字体状态恢复。
- 已存在 UI 的定期刷新、失效对象清理、撤销挂钩及释放自建字体。

当前类使用静态状态，一个 Unity 进程只能启用一份配置；所有调用在 Unity 主线程进行。作品派生类与公共源码直接编译进同一插件，不另发公共 DLL。这里保留现有调用模型，未扩展为多租户服务。

## 作品与引擎适配层的分工

第八作的 `UiLocalization.cs` 只保留插件 ID、字体候选、技术字符串和姓名确认句格式。`UiLocalizationData.cs` 仍由作品生成。正文排版、VM 指令、笔记本与菜单不属于此层。

实际对照第八、九作原程序集：Steezy 本地化组件 16 个方法、CharacterInputDialog 17 个方法及 Socotra DrawString/DrawChars 方法体一致。因此放在跨版本公共层，而非 `gmode-20050817`。第九作尚未接入或实机验证，不能把此比较理解为整套汉化兼容；特别是两作 RenderStart/RenderEnd 不同，不在这里复用绘图生命周期。

## 验证

在 `translation_workspace` 运行：

```powershell
.venv/Scripts/python.exe games/08-kibu8/scripts/build_bepinex.py
```

也可单独运行 `.venv/Scripts/python.exe engine/adapters/gmode-v2/ui/tests/run.py`。该测试直接编译公共生产代码和第八作配置，用 Unity/Harmony 替身验证整串替换、姓名确认、输入框保护、缓冲不变、冲突检测与卸载恢复；它不验证真实 Harmony 派发或 Unity 字体显示。

构建直接编译公共源码并执行上述测试及第八作绑定、字体、菜单和历史回归。真实 Unity 字体与输入显示仍需实机验证。新增作品应核对其 UI 方法签名与行为，提供自己的配置，并增加该作品的回归入口。
