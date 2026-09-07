# G-MODE 双篇运行适配器

第四作的 appli1.CanvasEx 与 appli2.CanvasEx 分别加载 sirasagi-1.res、sirasagi-2.res。DualCanvasHooks.cs 为两个类型分别缓存字段、校验场景范围并接入上下文译文，不共享跨类型 FieldInfo。

构建复用公共 engine/bepinex/build.py、engine/core 以及 gmode-v1/src 的点阵字体、菜单记忆与 DialogueReflow。公共既有源文件未改动。第四作 Plugin 为两套 Read、Script、Jump、ExeText、InitCanvasEx 安装挂钩；共享 Unity UI/字体/本地化只挂一次。字段状态按 canvas 实例隔离，初始化新游戏时清理会话状态。

只有含实际译文的脚本启用重排；原文透传脚本仍执行原生协程。第四作固定标题与名单地址保存在本作 FixedCardLayout，未继承旧作地址。

已用第四作原程序集实际执行前后篇读取挂钩，并对两份物理 subscn、上下文替换、原始游标/跳转/字节、菜单隔离与字面量替换进行离线验证。游戏窗口未启动，实机由用户验证。详见 games/04-shirasagi/RUNTIME_DELIVERY.md。
