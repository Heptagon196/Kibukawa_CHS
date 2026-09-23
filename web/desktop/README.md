# 癸生川网页番外桌面版

这是三部网页番外的 Tauri 2 桌面壳。它不改写游戏引擎；portable ZIP 中的 `www/` 明文保存主页与三个 `web/*/build/`，EXE 只负责窗口和安全的本地资源读取。

## 前置构建

先在仓库根目录按照 [`web/README.md`](../README.md) 下载原作资源并构建三部游戏：

```powershell
.\.venv\Scripts\python.exe web\fetch_sources.py
.\.venv\Scripts\python.exe web\fetch_pyxel_runtime.py
.\.venv\Scripts\python.exe web\build_birthday.py
.\.venv\Scripts\python.exe web\build_operation.py
.\.venv\Scripts\python.exe web\build_saina.py
```

还需要 Rust、Microsoft C++ Build Tools、Node.js，以及 Windows WebView2。Windows 10/11 通常已经自带 WebView2。

## 开发运行与 portable 打包

```powershell
cd web\desktop
npm install
npm run dev
npm run build
```

`npm run build` 只生成 release EXE，不生成安装器，并将可执行文件、明文 `www/`、使用说明及第三方许可整理到：

`portable/Kibukawa-Web-Spinoffs-CHS-v0.1.0-win64-portable.zip`

构建前会重新生成 `dist/`，并在任一游戏缺少 `build/index.html` 时立即报出明确错误。

三部作品的运行器、字库与游戏资源均从 portable 包的 `www/` 本地加载，游玩时无需联网。
