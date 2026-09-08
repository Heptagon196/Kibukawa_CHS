# GitHub Release 发布规则

## 补丁包命名（用户指定）

固定格式：`癸生川凌介 {编号:02d}-{游戏名}-CHS.zip`。

“癸生川凌介”后保留一个半角空格；编号使用十进制两位补零（`%02d`）；编号、游戏名与CHS之间使用半角连字符。ZIP名称不加版本号、时间戳、BepInEx或Full后缀；版本记录在Release标题、说明和清单中。

- 癸生川凌介 01-假面幻想杀人事件-CHS.zip
- 癸生川凌介 02-海楼馆杀人事件-CHS.zip
- 癸生川凌介 03-死者乐园-CHS.zip

名称登记在 `series/release-names.json`。新增作品沿用规则，并登记正式中文游戏名。

## GitHub 文件名限制

2026-09-07实测：GitHub会自动删除Release资产文件名中的中文和空格，上传后调用重命名API也无法保留。以上中文命名规则仍用于本地补丁ZIP及GitHub资产显示名（label）；GitHub实际下载文件名使用 `series/release-names.json` 中的 `github_name` 英文别名。

- Kibukawa-01-KamenGensou-CHS.zip → 癸生川凌介 01-假面幻想杀人事件-CHS.zip
- Kibukawa-02-Kairou-CHS.zip → 癸生川凌介 02-海楼馆杀人事件-CHS.zip
- Kibukawa-03-ShishaNoRakuen-CHS.zip → 癸生川凌介 03-死者乐园-CHS.zip

两种名称指向完全相同的ZIP字节。Release中的SHA256SUMS.txt使用实际下载的英文名，发布清单同时记录中文原名和英文下载名。发布说明须明确该限制，不宣称GitHub下载名可保持中文。

## 发布流程

发布前必须核对整个本作术语表及配套规则：所有新增且已确认、完成审校的术语均已并入 `series/glossary.json`，并与本作锁定表一致；别名、身份揭露和时间线用法须有备注。未确认项单独记录，不混入公共定译。此项也是宣布本作翻译完成的必要检查，不能以本作已有锁定术语表代替公共归并。具体规则见 `series/style.md` 的“名称与推理线索”。

1. 使用各作 `build --game kibuN` 完成构建和对应离线回归。公共适配器修改后，构建回归所有受影响作品；不自动安装或启动游戏。
2. 运行 `.venv/Scripts/python.exe tools/package_release.py --game <作品ID> --output out/github-release/<发布标识>`。工具核验点击单元审校基线、构建版本、源代码/译文哈希、ZIP完整性和包内文件哈希，再按上面的名称复制已验证ZIP，不重新压缩或加入原游戏文件。
3. 提交发布范围内源码、译文、文档及 `releases/<日期>/` 发布清单，推送GitHub；其他作品正在进行的改动保持独立。
4. Release标签指向本次提交，上传独立作品ZIP；将工具生成的SHA256SUMS.github.txt以SHA256SUMS.txt的名称上传。说明每作版本、安装方法、离线验证范围与尚待确认的实机事项。
5. 上传后核对Release资产名称、大小与SHA256；有摘要时核对GitHub摘要，无摘要时下载校验。公开发布后不要覆盖旧Release资产，修订发布使用新的标签。

## 通用图片替换完整包

先完成各作正文 build，再运行 `.venv/Scripts/python.exe tools/build_image_replacements.py`，最后运行：

```powershell
.venv/Scripts/python.exe tools/package_release.py --game <作品ID> --with-images --output out/github-release/<发布标识>
```

`--with-images` 校验正文与图片插件各自的源文件、资源版本、ZIP成员和哈希后合并完整包。正文功能文件须逐字节保持不变；面向玩家的说明在最终组包时统一整理。
图片插件目录为 `BepInEx/plugins/KibukawaImageReplacements`，版本与正文插件独立记录。作品专用图片替换的保留路由见图片插件说明。
标题 PNG 是中文本地化衍生图，原作品图像权利归原权利人。通用插件的离线测试不等同于全部实机视觉验收。

ZIP直接解压到对应游戏exe目录。下载者应自行拥有原游戏；补丁包含框架、插件、译文与字体许可，不包含原游戏程序、剧情资源或个人存档。

## Release 说明维护

新增作品直接更新开头的统一下载表格，并同步通用安装、内容和校验说明；不在末尾追加按日期或作品排列的重复发布段落。表格行之间不得插入空行。写入发布说明前统一为 LF，避免 Windows 文本写入把已有 CRLF 转成 CRCRLF。上传后用 GitHub Markdown 渲染检查表格。

## 历史记录完整包

需要合入历史记录时，先运行 `.venv/Scripts/python.exe engine/history/build.py`，再给 `tools/package_release.py` 添加 `--with-history`。组包校验历史插件源码指纹、DLL和许可证，保留正文与图片包原有成员。

## 玩家说明

完整包根目录只保留一份 `README.txt`，由 `series/README_PATCH.txt` 生成。内容限于安装、常用操作和反馈方式，使用普通玩家能理解的语言。各插件的开发说明不随完整包重复分发；许可证保留原有内容。
