"""Use open-source JPEXS to patch one AVM1 button function in the build copy."""
from pathlib import Path
import subprocess


def patch(source, destination, vendor, reports):
    java = vendor / 'java/jdk-21.0.9+10-jre/bin/java.exe'
    ffdec = vendor / 'ffdec/ffdec-cli.jar'
    export = reports / 'engine-source'
    relative = Path('DefineSprite_146_Parts_Button/frame_1/DoAction.as')
    edited = reports / 'engine-patch' / relative
    reports.mkdir(parents=True, exist_ok=True)

    def run(*args):
        result = subprocess.run([str(java), '-jar', str(ffdec), *map(str, args)],
                                cwd=reports, capture_output=True, text=True, encoding='utf8', errors='replace')
        with (reports / 'jpexs-build.log').open('a', encoding='utf8') as log:
            log.write(result.stdout + result.stderr)
        result.check_returncode()

    run('-export', 'script', export, source)
    text = (export / 'scripts' / relative).read_text('utf8')
    anchor = 'function ChgCaptionWidth(arg_width)\n{'
    if text.count(anchor) != 1:
        raise ValueError('Unexpected button engine source; refusing to patch')
    # Ruffle defers automatic text sizing. Flush both measurements before this
    # function sets autoSize=false and fixes the caption width. Otherwise the
    # previous zero-height field survives and its text is clipped away.
    insertion = '''
   var measuredWidth = Caption_txt._width;
   var measuredHeight = Caption_txt._height;
   var measuredShadowWidth = Caption_Shadow_txt._width;
   var measuredShadowHeight = Caption_Shadow_txt._height;'''
    edited.parent.mkdir(parents=True, exist_ok=True)
    edited.write_text(text.replace(anchor, anchor + insertion), encoding='utf8')
    run('-importScript', source, destination, reports / 'engine-patch')
    if not destination.exists() or destination.read_bytes() == source.read_bytes():
        raise ValueError('JPEXS did not produce a modified engine')
