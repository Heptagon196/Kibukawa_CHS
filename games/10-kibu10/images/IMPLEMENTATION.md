# 第十作 UI 与图片汉化

`inspect_image_coverage.py` 只读扫描 Resources、全部 StreamingAssets 包与 scratch 容器。当前得到 342 张可解码纹理（含副本），25 个空的动态字体 atlas；6 张联系表已逐张查看，逐纹理处置保存在 `coverage.reviewed.json`。库存 PNG/JPG 仅本地研究，Git 忽略；重新执行盘点可生成。

## 图片入口

- 16 个公共命名图片路由：4 个角色姓名牌、已通关状态、3 个标题菜单，分别覆盖 `LoadGraphic` 与 `Image_createImage`。
- `LoadGraphic2` 是本作标题亮度动画入口。12 个变体对应 3 菜单 × 900/700/500/400，按原 IL 的 1024 除数计算。`PaintTitle` 的 8 帧序列 `0,1,2,3,4,3,2,1` 与原程序集 RVA 数据一致。
- 标题三个状态使用相同代码排版标签，覆盖原选中动画区域，避免整图美术文字与另绘高亮笔形不一致而重影。保持三个原坐标及鼠标/键盘控制逻辑。
- 标题前篇、后篇、scratch 备用标题、外壳封面和警署背景可读牌匾使用 `image_gen` 编辑后的完整 PNG。五个最终文件与审阅见 `artwork/mapping.json`、`artwork/REVIEW.md`。生成图比原图大，运行时仅将其采样到原生 240×240、354×354 或 240×116 视口，包内 PNG 不改写。
- 4 页外壳帮助由空白画布重新排版为 930×632；控制说明与原图逐项核对，帮助页模型和 `ChangePage` 的 1–4 页号已验证。不会继承第九作独有的方向切换或自动存档提示。
- 外壳品牌 logo 复用发行商附带的英文 `*_en` 精灵。

本作 `ResourcesManager` 是单个 root 指针，而第八作是 root 列表；`scratch1.dat` 名长字段为 1 字节。这两点在本作离线图片库存脚本中按实物校验，不复制或新增公共 runtime adapter。公共 `NamedImageRuntime`、`ReplacementManifest`、`TextureReplacement` 与公共 BepInEx 编译/依赖锁完整复用。

匿名 `???`、输入按键与品牌英文保留；`rubi` 是原始字体 atlas，不当作一句日文翻译。主运行时确认中文正文清空原 ruby 行。背景图中不可辨的极小装饰书法不臆测文字，也不宣称有可靠译文。

## 构建与检查

```powershell
.venv/Scripts/python.exe games/10-kibu10/scripts/inspect_image_coverage.py
.venv/Scripts/python.exe games/10-kibu10/scripts/test_ui_images.py
.venv/Scripts/python.exe games/10-kibu10/scripts/build_image_replacements.py
```

构建入口 `build(framework=None)` 返回相对 package 路径到实际文件的映射，由主构建器组包。原始游戏资源 SHA256 在插件启动时复核；小图 payload 经公共 manifest 复核。所有图像创建为独立拥有的纹理，不改原资源，销毁时清理。实际游戏显示、标题动画与外壳切换仍需用户实机验证；本流程不安装、不启动、不操作窗口。
