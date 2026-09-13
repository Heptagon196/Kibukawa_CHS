# 系列公共 12px 字库

使用 Z Labs Pixel 12px M CN，来源固定到 zlabs-12px.lock.json 的提交。运行 `python engine/fonts/fetch_zlabs.py` 下载 KBITX 点阵和许可，核对大小及 SHA256；构建仅使用已验证的本地缓存。

`engine/tools/zlabs_font.py` 通过 kbitfont 0.0.4 读取上游字距、字形边界、基线和像素透明度，不缩放，不混字，不使用手工补字。字体二进制缓存不提交。

作者 Astro_2539，字体采用 OFL-1.1。衍生图集名称为 Kibu8 UI Pixel 12；包内保留完整许可及来源说明，不附源字体或构建 JSON。

第八作正文使用 Unifont 16px，12px 界面和指令图标使用本库。构建独立检查实际小字号字符集，正文专用 ∇、⊂、尐、牸由 Unifont 显示。
