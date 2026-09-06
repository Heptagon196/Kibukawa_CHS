# BepInEx 公共构建层

`build.py` 不导入任何作品的 pipeline。统一处理依赖下载、SHA256校验、损坏缓存修复、Mono插件编译、完整框架组装和ZIP校验。

- `profiles/`：后端、平台、架构与依赖锁的对应关系。
- `locks/`：固定版本的官方下载地址、大小与哈希。
- `licenses/`：框架原始许可文件。
- `tests/`：公共层回归测试。
- 系列根目录 `cache/bepinex/<profile>/`：共享下载缓存，不进入 Git。解压路径还包含依赖哈希，避免版本混用。

每作 `project.json` 的 `bepinex` 指定 profile、Managed目录、输出程序集名、插件目录名和程序集引用；构建脚本提供源码列表与打包文件映射。公共层不假设第一作的安装路径或插件名。

目前已验证 Mono / Windows x64 / BepInEx 5.4.23.5。遇到 IL2CPP 或其他后端，需实现相应编译路径并验证后才能增加配置，不能只改 profile 声称支持。游戏专用挂钩、译文导出、字体子集生成、特殊界面与实际指令回放仍由对应作品和引擎适配器负责。

先构建任一使用当前 profile 的作品准备缓存，然后运行：

```powershell
.venv/Scripts/python.exe engine/bepinex/tests/test_build.py
```

测试模拟网络响应并写入忽略的 cache/bepinex-tests，不修改游戏。
