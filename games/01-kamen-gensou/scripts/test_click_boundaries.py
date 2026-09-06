"""Regression: conserving total text must not hide moving words across a wait."""
import copy
from check_click_boundaries import units

def command(offset,opcode,text=''):
    return dict(script='regression',instruction=offset,opcode=opcode,
                strings=[text] if opcode==72 else [],expected=[text] if opcode==72 else [])

def main():
    original=[command(0,72,'也是您的邻居！'),command(1,79),
              command(2,72,'我是林居刑警。'),command(3,76)]
    broken=copy.deepcopy(original)
    broken[0]['expected'][0]+='我是'
    broken[2]['expected'][0]='林居刑警。'
    good=units(original);bad=units(broken)
    assert ''.join(u['target'] for u in good)==''.join(u['target'] for u in bad)
    assert good!=bad, 'Cross-wait text movement must be detected'
    split=[command(0,72,'也是您的'),command(1,77),command(2,72,'邻居！'),command(3,79)]
    assert units(split)[0]['target']=='也是您的邻居！', 'Newline must not split click units'
    assert [u['target'] for u in good]==['也是您的邻居！','我是林居刑警。']
    print('PASS: cross-wait movement detected despite conserved full text; newline stays within unit.')

if __name__=='__main__': main()
