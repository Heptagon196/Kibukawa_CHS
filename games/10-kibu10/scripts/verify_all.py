"""Offline verification only; does not install or launch any game."""
import argparse
import subprocess
import sys
import pipeline as p

def set_semantic_release_state(complete, **evidence):
    """Persist a conservative state even when a later release check fails."""
    cache=p.load(p.WORK/'work/cache.json')
    cache.setdefault('extra',{}).update(semantic_release_review_complete=complete,**evidence)
    p.save(p.WORK/'work/cache.json',cache)

def verify(smoke=False):
    before=p.game_hashes()
    prior=p.first_project_hashes()
    p.validate_sources()
    if not smoke:
        set_semantic_release_state(False,translation_stage='review_required')
    commands=[
        [sys.executable,str(p.PROJECT['adapter_path']/'test_vm.py')],
        [sys.executable,str(p.WORK/'scripts/test_translation_build.py')],
        [sys.executable,str(p.WORK/'scripts/test_quality_gate.py')],
        [sys.executable,str(p.WORK/'scripts/test_ui.py')],
        [sys.executable,str(p.WORK/'scripts/test_ui_images.py')],
        [sys.executable,str(p.WORK/'scripts/test_layout_context.py')],
        [sys.executable,str(p.WORK/'scripts/check_ui.py')],
        [sys.executable,str(p.WORK/'bepinex/tests/test_runtime_abi.py')],
        [sys.executable,str(p.WORK/'bepinex/tests/test_info_widths.py')],
        [sys.executable,str(p.WORK/'bepinex/tests/test_history_bindings.py')],
        [sys.executable,str(p.WORK/'bepinex/tests/Run-UiRuntimeTests.py')],
    ]
    commands += [[p.shell(),'-NoProfile','-File',str(p.WORK/'bepinex/tests'/name)] for name in
        ('Run-DirectRuntimeTests.ps1','Run-TitleOverlayStartupTests.ps1','Run-DirectChoiceMemoryTests.ps1','Run-DirectPackBindingTests.ps1','Run-HistoryTests.ps1')]
    evidence=[]
    for command in commands:
        result=subprocess.run(command,check=True,capture_output=True,text=True,encoding='utf-8',errors='replace')
        evidence.append(dict(command=command,output=result.stdout+result.stderr))
        print((result.stdout+result.stderr).strip())
    from translation import collect
    from translation_review import check
    from quality_gate import check as check_quality
    audit=collect()
    review=check(strict=not smoke)
    quality=check_quality(strict=not smoke)
    if not smoke:
        p.require(audit['pending']==0 and not audit['findings'],'Missing/unreviewed text')
        set_semantic_release_state(True,translation_stage='reviewed',
            reviewed_dialogue_sha256=p.sha((p.WORK/'work/dialogue-tagged.json').read_bytes()),
            click_review_sha256=p.sha((p.WORK/'work/click_boundaries.reviewed.json').read_bytes()),
            color_review_sha256=p.sha((p.WORK/'research/color-spans.reviewed.json').read_bytes()),
            quality_gate_sha256=p.sha((p.WORK/'reports/quality-gate.json').read_bytes()))
    subprocess.run([sys.executable,str(p.SERIES/'tools/check_text_style.py'),'--game','kibu10'],check=True)
    p.require(before==p.game_hashes() and prior==p.first_project_hashes(),'Protected-file hashes changed during verification; check concurrent external changes')
    report=dict(schema=1,smoke=smoke,checks=evidence,audit=audit,review=review,quality=quality,
                original_game_unchanged=True,previous_translation_work_unchanged=True,runtime_tested=False,
                protection_scope='Before/after this verification interval only; external task changes elsewhere in the session are outside this comparison.')
    p.save(p.WORK/'reports'/('verify-smoke.json' if smoke else 'verify-all.json'),report)
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--smoke',action='store_true')
    verify(parser.parse_args().smoke)
