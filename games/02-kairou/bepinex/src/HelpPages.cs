// Generated from independently reviewed kibu2 help content by build_help_pages.py.
namespace Kibu1ZhCN {
    public sealed class HelpPage { public string Name, Title, Subtitle, Footer, Body; public string[][] Rows; }
    public static class HelpPages {
        public static readonly HelpPage[] All = new HelpPage[] {
            new HelpPage { Name="howtoplay_keyguide_steam_00", Title="操作说明", Subtitle="〈侦探·癸生川凌介事件谭 第2卷《海楼馆杀人事件》〉", Rows=new string[][] { new [] { "START 按钮", "选项" }, new [] { "A 按钮", "确认／推进文字" }, new [] { "L 摇杆／方向键", "移动光标" }, new [] { "L 摇杆向下／方向键下", "跳过文字" }, new [] { "R", "切换声音 ON／OFF" } }, Footer="本游戏不支持自动保存。\n退出前，请使用游戏内的存档功能保存进度。", Body="" },
            new HelpPage { Name="howtoplay_keyguide_steam_01", Title="操作说明", Subtitle="〈侦探·癸生川凌介事件谭 第2卷《海楼馆杀人事件》〉", Rows=new string[][] { new [] { "ESC", "选项" }, new [] { "Z / SPACE / L SHIFT / L CTRL", "确认／推进文字" }, new [] { "W A S D / ↑ ← ↓ →", "移动光标" }, new [] { "S / ↓", "跳过文字" }, new [] { "E", "切换声音 ON／OFF" } }, Footer="本游戏不支持自动保存。\n退出前，请使用游戏内的存档功能保存进度。", Body="" },
            new HelpPage { Name="howtoplay_keyguide_steam_02", Title="G-MODE 经典游戏复刻", Subtitle="", Rows=null, Footer="", Body="“G-MODE 经典游戏复刻”是一项复刻计划，\n旨在忠实重现昔日功能手机上的游戏，\n让玩家再次体验它们当年的风貌。\n\n※ 从功能手机版移植时，为了让游玩更加舒适，\n我们对部分操作方式和功能进行了调整。\n\n※ 游戏内的操作说明及菜单仍保留原版内容。\n本作的实际操作方式，请参阅本菜单中的“玩法说明”。" },
            new HelpPage { Name="howtoplay_keyguide_steam_03", Title="G-MODE 经典游戏复刻", Subtitle="", Rows=null, Footer="", Body="〈注意事项〉\n\n为忠实重现当年的手机版游戏，\n游戏中可能仍会显示部分无法使用的菜单或按钮，\n例如“WEB（网站）”“目录”“背光”等。\n\n帮助等页面中可能保留了有关通信费用的说明，\n但游玩本作不会另行产生通信费用。" }
        };
        public static HelpPage Find(string name) {
            foreach (var page in All) if (page.Name == name) return page;
            return null;
        }
    }
}
