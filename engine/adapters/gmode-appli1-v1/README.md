# G-MODE 单篇 appli1 适配

第五作使用单套appli1.CanvasEx。正式作品入口及帮助页/固定卡片策略位于games/05-kurai-hako/bepinex/src，直接编译公共engine/core和gmode-v1/src的字体、DialogueReflow、菜单记忆代码。

Read完成后按原始instruction+slot与源文匹配替换，不改脚本字节或游标。原始Read/Jump/ExeText、完整正文重排及生产菜单transpiler均有第五作独立离线回放验证。

公共BepInEx构建层负责依赖校验、编译及组包。帮助图由作品插件接入；标题等原生图片替换见 `engine/image-replacements`。离线回放不代替实机验证。
