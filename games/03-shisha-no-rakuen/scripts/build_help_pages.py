"""Compile independently verified kibu3 help sprites (static asset review only)."""
import json
import UnityPy
import pipeline as p
ROOT = p.WORK / 'bepinex'
BUNDLE = 'kibu3_Data/StreamingAssets/prefab/howtoplay'
SHA256 = '21c32932831f7205bafc4525e0fd953c0aad23213f432d33ce1be0a2bd4f49f3'
IDS = [2778766535315927420, 6042102281722460859, -5840363736877972196, 3367658281433840671]
# Independently transcribed against the four kibu3 texture exports on 2026-09-06.
# White text is visible after compositing the RGBA export against navy blue.
PAGES = [
 dict(title='操作说明', subtitle='〈侦探·癸生川凌介事件谭 第3卷《死者乐园》〉',
      rows=[['START 按钮','选项'],['A 按钮','确认／推进文字'],['L 摇杆／方向键','移动光标'],['L 摇杆向下／方向键下','跳过文字'],['R','切换声音 ON／OFF']],
      footer='本游戏不支持自动保存。\n退出前，请使用游戏内的存档功能保存进度。'),
 dict(title='操作说明', subtitle='〈侦探·癸生川凌介事件谭 第3卷《死者乐园》〉',
      rows=[['ESC','选项'],['Z / SPACE / L SHIFT / L CTRL','确认／推进文字'],['W A S D / ↑ ← ↓ →','移动光标'],['S / ↓','跳过文字'],['E','切换声音 ON／OFF']],
      footer='本游戏不支持自动保存。\n退出前，请使用游戏内的存档功能保存进度。'),
 dict(title='G-MODE 经典游戏复刻', body='“G-MODE 经典游戏复刻”是一项复刻计划，\n旨在忠实重现昔日功能手机上的游戏，\n让玩家再次体验它们当年的风貌。\n\n※ 从功能手机版移植时，为了让游玩更加舒适，\n我们对部分操作方式和功能进行了调整。\n\n※ 游戏内的操作说明及菜单仍保留原版内容。\n本作的实际操作方式，请参阅本菜单中的“玩法说明”。'),
 dict(title='G-MODE 经典游戏复刻', body='〈注意事项〉\n\n为忠实重现当年的手机版游戏，\n游戏中可能仍会显示部分无法使用的菜单或按钮，\n例如“WEB（网站）”“目录”“背光”等。\n\n帮助等页面中可能保留了有关通信费用的说明，\n但游玩本作不会另行产生通信费用。')
]

def build_help_pages():
    bundle = p.GAME / BUNDLE
    p.require(p.sha(bundle.read_bytes()) == SHA256, 'Third-game help bundle mismatch')
    objects = {o.path_id:o for o in UnityPy.load(str(bundle)).objects}
    refs = objects[-4575662690838675561].read_typetree()['howToPlayImages']
    p.require([r['m_PathID'] for r in refs] == IDS, 'Third-game help order/count mismatch')
    entries, pages = [], []
    q = lambda v: json.dumps(v, ensure_ascii=False)
    for i, (sid, page) in enumerate(zip(IDS,PAGES)):
        sprite = objects[sid].read_typetree()
        name = 'howtoplay_keyguide_steam_%02d' % i
        p.require(sprite['m_Name'] == name, 'Help sprite name mismatch')
        p.require(sprite['m_Rect']['width'] == 930 and sprite['m_Rect']['height'] == 632, 'Help dimensions changed')
        rows = 'null' if 'rows' not in page else 'new string[][] { '+', '.join('new [] { '+q(a)+', '+q(b)+' }' for a,b in page['rows'])+' }'
        entries.append('new HelpPage { Name='+q(name)+', Title='+q(page['title'])+', Subtitle='+q(page.get('subtitle',''))+', Rows='+rows+', Footer='+q(page.get('footer',''))+', Body='+q(page.get('body',''))+' }')
        pages.append(dict(name=name, sprite_path_id=sid, sprite_sha256=p.sha(objects[sid].get_raw_data()), translation=page))
    source = '''// Generated from independently reviewed kibu3 help content by build_help_pages.py.
namespace Kibu1ZhCN {
    public sealed class HelpPage { public string Name, Title, Subtitle, Footer, Body; public string[][] Rows; }
    public static class HelpPages {
        public static readonly HelpPage[] All = new HelpPage[] {
            ''' + ',\n            '.join(entries) + '''
        };
        public static HelpPage Find(string name) {
            foreach (var page in All) if (page.Name == name) return page;
            return null;
        }
    }
}
'''
    p.inside(ROOT/'src/HelpPages.cs').write_text(source,encoding='utf-8-sig')
    report = dict(page_count=4,translated_pages=4,source_bundle=BUNDLE,source_bundle_sha256=SHA256,pages=pages,
                  static_source_images_reviewed=True,runtime_visual_tested=False,
                  image_scope='Only the four wrapper help pages are reconstructed. Title artwork and other baked game images remain unmodified/unverified.')
    p.save(ROOT/'build/help-pages-report.json',report)
    return report

if __name__ == '__main__': print(json.dumps(build_help_pages(),ensure_ascii=False))
