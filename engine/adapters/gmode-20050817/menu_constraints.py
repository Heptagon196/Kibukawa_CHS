"""Identify native short command labels from decoded menu declarations."""
def short_choice_offsets(commands):
    mode=None
    for command in commands:
        if command['name'] in ('KOMANDO','CHOUBUN_KOMANDO','ICON_KOMANDO','JIYUU_KOMANDO'):
            mode=command['name']
        if command['name']=='SENTAKUSI' and mode=='KOMANDO':
            yield command['offset']
