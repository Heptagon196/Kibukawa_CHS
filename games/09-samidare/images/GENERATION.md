# 第九作图片本地化

全量目视核查 `scratch1.dat` 的 131 张 GIF/JPG 与 Unity 外壳纹理后，玩家可见且需要本地化的图片共四项：游戏内标题、两张标题菜单选中态、Unity 外壳封面。`rubi.gif` 是日文注音字形表，译文行由运行时关闭注音，不是界面图片。`scratch1.dat/title.gif` 是未被本作 `Game_title` 引用的旧副本；实际游戏内标题由 `resource:///title.gif` 读取 `resources.assets` 的 `title` 纹理。

`generate_images.py` 从本机已校验的原版 `resources.assets`/`resources.assets.resS` 读取 `title`（240×240）和 `titleimage`（354×354），仅清除原日文文字区域，再用锁定哈希的 Noto Serif SC 绘制中文。标题固定为“五月雨是铅灰的旋律”，标题菜单为“从头开始”“继续游戏”。两张 87×19 透明高亮精灵使用同一字体和描边规则生成。背景、英文副题与版权行来自原图，未由生成模型重绘。

重建命令：

```powershell
.\.venv\Scripts\python.exe games\09-samidare\images\generate_images.py
```

最终文件为 `title-zh.png`、`titleimage-zh.png`、`title-menu0-zh.png`、`title-menu1-zh.png`。生成器先核对原游戏指纹和字体哈希；尺寸或来源变化会立即失败。

曾用内置 imagegen 的 `text-localization` 模式做过一次候选编辑，提示要求逐字替换系列名、主标题和菜单，并完整保留雨巷、英文副题和版权。候选图改变了雨巷内容，未作为成品。最终资源采用上述确定性像素流程，以保证文字、构图和复现性。
