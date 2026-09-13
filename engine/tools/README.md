# 公共字体构建工具

这些 Python 模块供作品构建脚本导入。它们不选择剧情、不决定译文字符集，也不安装游戏补丁。

| 模块 | 作用 |
| --- | --- |
| `pixel_font.py` | 读取 Unifont HEX 点阵，提供无损 PNG 编码 |
| `bdf_font.py` | 读取 BDF 原生点阵、字距与字形边界 |
| `zlabs_font.py` | 读取已锁定的 Z Labs 字库及原生透明度；来源锁和获取脚本见 `../fonts/README.md` |
| `kbf3_atlas.py` | 把已摆放的字形编码为 KBF3 索引和 RGBA 图集，不缩放、不重新排版 |
| `test_kbf3_atlas.py` | 验证 KBF3 字距、bearing、透明度、空字形及非法记录处理 |

## KBF3 编码器

```python
from kbf3_atlas import encode_kbf3

index, rgba = encode_kbf3(pixel_size, width, height, glyphs)
```

每个 `glyphs` 元素是：

```text
(codepoint, x, y, advance, width, height, bearing_x, bearing_y, alpha_bytes)
```

坐标和 alpha 行按从上到下排列，alpha 长度必须等于字形宽×高；bearing 可以为负。返回值都是 `bytes`。函数校验重复码点、越界位置及像素长度，但不负责选择字形位置或避免调用方安排的重叠。空字形可保留非零字距。

`transparent_white=True` 保留字形矩形内部透明像素的白色 RGB，以兼容已有 Pillow 罗马音图集；默认透明像素为零。该选项不改变 alpha 或可见像素。

KBF3 头部为 5 个小端 int32：magic `KBF3`、名义字号、图集宽、高、字形数量。随后每条记录为 8 个小端 int32，即上述元组除 alpha 以外的字段。图集 PNG 由调用者保存。读取实现见 `../adapters/gmode-v2/src/BitmapFontAtlas.cs`；编码格式不依赖该 VM 的剧情行为。

第八作目前两个调用者：

- `build_pixel_font.py`：选择 Z Labs 字形、字号、排列和透明度，调用编码器生成 UI 图集。
- `build_notebook_font.py`：选择 Pillow 罗马音字形及其排列，调用编码器生成姓名读音图集。

字体下载、来源锁、许可复制、字符收集、输出目录和报告仍归作品构建流程负责。公共编码器不读写文件、不联网。

## 验证

在 `translation_workspace` 运行：

```powershell
.venv/Scripts/python.exe -m unittest discover -s engine/tools -p test_kbf3_atlas.py
```

第八作完整构建也运行以上测试，并验证原生字形像素、缺字和运行时几何。修改编码器时应回归所有调用者；仅通过编码测试不能代替完整字体构建。
