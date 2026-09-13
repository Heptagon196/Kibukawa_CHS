# 公共 UI 汉化素材库

本目录保存可按样式复用的中文 UI 图片，与运行时图片替换代码分开。作品的资源路径、章节编号和加载器仍由各作 `images/replacements.json` 指定。

## 文件用途

| 路径 | 用途 |
| --- | --- |
| `catalog.json` | 稳定素材 ID、PNG 路径、尺寸、目标文件哈希、适用原图 RGBA 指纹与来源 |
| `zh-CN/classic-240/` | 当前 240px 样式的 10 个双状态指令按钮、3 个标题菜单按钮、设置页，以及指令按钮修补底图 |
| `ui_asset_catalog.py` | 读取素材，校验文件哈希/尺寸/路径，并检查适用原图；不安装、不修改 PNG |
| `test_ui_asset_catalog.py` | 验证全部素材、原图指纹拒绝、尺寸拒绝和禁止按文件名猜测匹配 |

这批图片来自第八作已有且经过用户使用的汉化美术，移动时未重新绘制。十个指令按钮的文字采用 Fusion Pixel 10px；原字库锁、许可打包仍由第八作 `build_command_icons.py` 管理。该脚本现在重建按钮并与公共素材逐像素比较，防止美术与构建参数脱节。标题全图、外壳封面、人物名牌和第八作笔记页面仍留作品目录。

## 如何引用

第八作图片构建器支持用 `sharedAsset` 代替本地 `png`：

```json
{
  "id": "option",
  "sharedAsset": "classic-240/option",
  "size": [240, 240],
  "sources": [{"loader": "LoadGraphic", "name": "option.jpg"}]
}
```

构建器调用 `resolve_asset(id)` 取得路径和记录，再对实际解析出的每张原图调用 `validate_source(entry, source)`。必须同时符合尺寸和 RGBA SHA256；相同文件名不能替代指纹验证。生成的游戏包仍是自包含的，不要求用户安装公共源码目录。

`command-backgrounds` 是构建模板，不允许作为整图替换。目录中图片视为构建输入；修改美术时应同步更新目录哈希、像素测试和来源说明，构建过程不回写它们。

## 已验证范围与新增样式

当前仅第八作已接入。实际比较第九作 scratch 图片和可解码 Resources 纹理，没有找到这 14 张替换图对应的相同原图；另有 4 张纹理未能解码，不能宣称完整排除。第九作不自动启用此样式，也未修改其安装目录。

其他作品接入前，需确认用途和资源路由，并通过原图指纹检查。如果外观/布局不同，应增加独立样式 ID，而不是把不同原图随意加入旧记录。通用指的是素材可由目录引用，不表示已经适用于所有作品。

## 验证命令

在 `translation_workspace`：

```powershell
.venv/Scripts/python.exe -m unittest discover -s engine/ui-assets -p test_ui_asset_catalog.py
.venv/Scripts/python.exe games/08-kibu8/scripts/build_bepinex.py
```

完整构建还核对实际原图、十个按钮的二十种状态，以及原有图片替换与标题菜单回归。
