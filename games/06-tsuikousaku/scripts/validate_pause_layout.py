"""Verify the actual original pause prefab assumptions; never launch Unity."""
import pipeline as p
import UnityPy

def validate():
    path=p.GAME/'kibu6_Data/StreamingAssets/prefab/setting'
    original=p.load(p.WORK/'work/manifest.json')['game_hashes']
    assert p.sha(path.read_bytes())==original[path.relative_to(p.GAME).as_posix()]
    objects={o.path_id:o for o in UnityPy.load(str(path)).objects}
    transforms={};names={}
    for i,o in objects.items():
        if o.type.name=='GameObject':names[i]=o.read_typetree()['m_Name']
        elif o.type.name=='RectTransform':transforms[i]=o.read_typetree()
    by_name={names[t['m_GameObject']['m_PathID']]:(i,t) for i,t in transforms.items()}
    root,rt=by_name['Dialog']
    for name,width in [('Contents',740),('BG',856),('DialogTitle',600)]:
        _,t=by_name[name]
        assert t['m_Father']['m_PathID']==root
        assert t['m_AnchorMin']==t['m_AnchorMax']=={'x':.5,'y':.5}
        assert t['m_AnchoredPosition']['x']==0 and t['m_SizeDelta']['x']==width
    children=by_name['Contents'][1]['m_Children']
    assert len(children)==8
    assert {names[transforms[c['m_PathID']]['m_GameObject']['m_PathID']] for c in children}=={'HowToPlay','FrameSetting','FilterSetting','WindowSetting','Ranking','BackTitle','Exit','Close'}
    print('PASS: original pause hierarchy, anchors, widths and all eight menu controls')
if __name__=='__main__':validate()
