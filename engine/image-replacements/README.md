# 癸生川通用图片替换

插件显示名称：`Kibukawa Image Replacements`。DLL 与安装目录：`KibukawaImageReplacements`，当前版本 1.1.0。
首批配置覆盖五作标题，以及第一作的两处标题和第四作前后篇。不限于标题，每作可配置多张完整替换图。

实现参考第二作 `FloorPlanOverlay.cs`：在 `CanvasEx.ReadImg(int)` 返回后，创建独立、无 mipmap 的纹理，上传 RGBA 像素并恢复正确所有权。
原游戏 GIF 解码、资源缓存与原图保持不变；尺寸不符、加载或纹理创建失败时保留原图。
支持带透明度的完整图片替换，不是对原始 GPU 纹理的局部叠字。

第二作原有楼层图与帮助页代码和文件保持原样；`CanvasEx:10` 保留给原楼层图替换，新配置构建时禁止占用。

## 添加或修改图片

编辑各作 `images/replacements.json`，PNG 路径相对于该作 `images/`：

```json
{
  "schema": 1,
  "game": "kibu4",
  "images": [
    {
      "id": "title",
      "png": "title-zh/title.png",
      "sources": [
        {"archive": "sirasagi-1.res", "member": "gif2", "index": 0, "canvas": "appli1.CanvasEx"},
        {"archive": "sirasagi-2.res", "member": "gif2", "index": 0, "canvas": "appli2.CanvasEx"}
      ]
    }
  ]
}
```

向 `images` 数组新增独立 id 和同尺寸 PNG 即可添加图片；同一 PNG 可配置多个来源。
当前支持这些游戏 `gif1` / `gif2` 表中、经 `ReadImg` 读取的原生图像，不覆盖 Unity 外壳帮助页、视频或未验证的新引擎。
第一至三作 canvas 为 `CanvasEx`；第四作分为 `appli1.CanvasEx`、`appli2.CanvasEx`；第五作为 `appli1.CanvasEx`。
构建工具校验原图尺寸，并自动计算 gif2 在运行时图片表中的偏移，无须手写运行时编号。

```powershell
./.venv/Scripts/python.exe tools/build_image_replacements.py --game kibu4
./tools/install_image_replacements.ps1 -Game kibu4 -CheckOnly
./tools/install_image_replacements.ps1 -Game kibu4
```

省略 `--game` / `-Game` 为五作。输出位于 `out/image-replacements-1.1.0/`。
运行时使用生成的 `image-replacements.tsv` 和 `images/*.rgba`；原 PNG 同包保留以便查阅。
TSV 头是格式版本、游戏进程名、原程序集 SHA256、scratchpad SHA256；随后每行为图片 id、canvas、运行时编号、RGBA 文件相对路径、SHA256。
重复路由、路径越界、资源损坏和原游戏版本不符均会被拒绝。

安装脚本将生成的通用图片插件及其配置复制到对应游戏目录，并核验文件哈希。
第二作已有 `Kibu2ZhCN` 插件目录完全不动。

## 验证

离线测试覆盖像素方向、透明度、无 mipmap 上传、不可读原纹理、资源所有权、缓存、错误回退、多图配置及第二作保留路由。
还检查五作实际程序集的 `ReadImg` 和纹理 API，以及新插件不再调用编码图片解码入口。
这些不等同于游戏窗口验收。替换成功日志为 `Replaced image <canvas>:<index> with independently owned RGBA texture`。

图片为原游戏素材的中文本地化衍生资源，原作图像权利归原权利人，非代码 MIT 许可内容。
