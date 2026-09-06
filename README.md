# 癸生川系列汉化工作区

仓库：`Kibukawa_CHS`。需要自行安装对应的正版游戏；仓库不包含游戏程序、原始资源或个人存档。

首次克隆后，安装 Python、PowerShell 7、.NET SDK 6+ 和 Windows .NET Framework 4.x，运行 `setup.cmd` 准备 Python 与 Mono.Cecil 依赖，再编辑 `series.json` 的安装路径。构建会从已校验的本机游戏恢复所需原文快照，保留仓库中的译文；BepInEx 和 Unifont 由构建脚本自动下载并校验。

公共代码与每作数据分开存放。当前已支持第一作，插件版本仍为 1.0.30；此次整理不改译文或游戏行为。

## 游戏路径配置

编辑根目录 `series.json`。`project` 和 `installation` **均相对于 series.json 所在目录**，与终端当前目录无关。

```json
{
  "schema": 1,
  "default_game": "kibu1",
  "games": {
    "kibu1": {
      "title": "假面幻想杀人事件",
      "project": "games/01-kamen-gensou",
      "installation": "..",
      "adapter": "gmode-v1",
      "enabled": true
    }
  }
}
```

当前工作区位于第一作安装目录内，所以 installation 是 `..`。第二作若与第一作安装目录并列，可以使用 `../../第二作安装目录`。路径支持中文、空格和 `..`。项目目录必须位于工作区内。

整个目录移到独立位置后，更新 installation 即可；Python 虚拟环境不保证可搬迁，必要时重新运行 setup.cmd。新增游戏先设 enabled=false，完成适配和兼容检查后再启用；登记路径不等于已经支持新引擎。

## 目录职责

```text
engine/core/                    译文包模型、二进制读取
engine/adapters/gmode-v1/src/   文字协程、菜单记忆、点阵绘制
series/                        系列人物译名与文风原则
games/01-kamen-gensou/
  project.json                 作品声明、审校路径、已验证排版参数
  scripts/                     本作提取、构建、校验、安装及修订工具
  bepinex/src/                 本作入口、聊天定位、名单和帮助页规则
  bepinex/tests/               本作回归用例、真实指令回放
  bepinex/*.lock.json          本作锁定的框架和字体依赖
  work/                        AiNiee cache.json、定位清单、术语、点击基线
  originals/、raw/、research/   原文快照与引擎研究
  translated_texts/            可读译文
  reports/                    本作检查报告
  out/                        本作新发布包
  installations/、save_backups/ 安装备份与用户存档备份
tools/                         系列命令与路径解析
bin/、.venv/                   本机工具环境
out/                          迁移前历史发布包，保留原下载路径
```

第一作唯一的活动译文源仍为 `games/01-kamen-gensou/work/cache.json`。系列术语是后续作品的继承基线，各作保留独立锁定快照；修改系列术语不自动替换旧译文。

## 使用

```powershell
.\run.ps1 list
.\run.ps1 paths --game kibu1
.\run.ps1 extract --game kibu1
.\run.ps1 status --game kibu1
.\run.ps1 build --game kibu1
.\run.ps1 install --game kibu1 -CheckOnly
.\run.ps1 install --game kibu1
```

build/verify 都执行完整 BepInEx 构建与校验，不安装、不启动游戏。安装前退出游戏；CheckOnly 只核验包与原游戏指纹。根目录 extract.cmd、build_bepinex.cmd、rebuild.cmd、verify.cmd 操作 default_game。旧版离线回填由 rebuild_legacy.cmd 单独进入，不用于正式发布。

新增作品需建立独立 project.json、脚本、译文和原文快照。引擎变更新增 adapter；公共代码改动后对所有启用作品执行构建回归。当前 gmode-v1 仍保留原命名空间 Kibu1ZhCN，尚未宣称适配任何未检查的续作。本作地址范围留在本作代码中。project.json 的排版值记录已验证参数，不能仅改配置就假定引擎缓冲也会改变。

构建报告记录公共代码和译文哈希；各作各有原文件指纹、点击基线与发布目录。旧报告中的绝对路径是历史记录，不应当作当前路径配置。
