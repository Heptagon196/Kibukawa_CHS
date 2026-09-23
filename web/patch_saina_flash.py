"""Use open-source JPEXS to patch SWF code/text in build copies."""
from pathlib import Path
import subprocess


def _runner(vendor, reports):
    java = vendor / 'java/jdk-21.0.9+10-jre/bin/java.exe'
    ffdec = vendor / 'ffdec/ffdec-cli.jar'
    reports.mkdir(parents=True, exist_ok=True)

    def run(*args):
        result = subprocess.run([str(java), '-jar', str(ffdec), *map(str, args)],
                                cwd=reports, capture_output=True, text=True, encoding='utf8', errors='replace')
        with (reports / 'jpexs-build.log').open('a', encoding='utf8') as log:
            log.write(result.stdout + result.stderr)
        result.check_returncode()
    return run


def patch(source, destination, vendor, reports):
    export = reports / 'engine-source'
    relative = Path('DefineSprite_146_Parts_Button/frame_1/DoAction.as')
    edited = reports / 'engine-patch' / relative
    run = _runner(vendor, reports)

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
    # SharedObject retains object references after flush. Subsequent save-point
    # cleanup deletes the old scene arrays in place; Ruffle flushes these mutated
    # references again on unload. Store detached snapshots, not live engine data.
    save_relative = Path('__Packages/Cls_SaveLoad.as')
    save_text = (export / 'scripts' / save_relative).read_text('utf8')
    clone = '''   function CloneSaveValue(value)
   {
      if(value == null || typeof value != "object") return value;
      var result = value instanceof Array ? new Array(value.length) : new Object();
      for(var key in value) result[key] = this.CloneSaveValue(value[key]);
      return result;
   }
'''
    save_text = save_text.replace('   function SaveGame(arg_no, arg_freeData1, arg_freeData2)', clone + '   function SaveGame(arg_no, arg_freeData1, arg_freeData2)')
    start = save_text.index('   function SaveGame(')
    end = save_text.index('   function LoadGame(', start)
    section = save_text[start:end]
    for obj in ('_loc2_', '_loc5_', '_loc3_', '_loc6_', '_loc7_'):
        anchor = f'      {obj}.flush();'
        assert section.count(anchor) == 1
        section = section.replace(anchor, f'      for(var saveKey in {obj}.data) {obj}.data[saveKey] = this.CloneSaveValue({obj}.data[saveKey]);\n' + anchor)
    save_text = save_text[:start] + section + save_text[end:]
    # Restoring must detach too: otherwise advancing after a load mutates the
    # SharedObject again even when that slot is never explicitly overwritten.
    start = save_text.index('   function LoadGame(')
    end = save_text.index('   function DeleteSaveData(', start)
    import re
    section, count = re.subn(r'var (_loc\d+_) = SharedObject.getLocal\(([^)]+)\);',
        r'var \1 = {data:this.CloneSaveValue(SharedObject.getLocal(\2).data)};', save_text[start:end])
    assert count == 5
    save_text = save_text[:start] + section + save_text[end:]
    save_patch = reports / 'engine-patch' / save_relative
    save_patch.parent.mkdir(parents=True, exist_ok=True)
    save_patch.write_text(save_text, encoding='utf8')
    run('-importScript', source, destination, reports / 'engine-patch')
    if not destination.exists() or destination.read_bytes() == source.read_bytes():
        raise ValueError('JPEXS did not produce a modified engine')


def patch_progress_bar(source, destination, notice, vendor, reports):
    """Localize the Japanese notice embedded in ProgressBar.swf."""
    verified = reports / 'progressbar-text-verified'
    run = _runner(vendor, reports)
    localized = notice.read_text(encoding='utf8').strip()
    run('-replace', source, destination, '2', notice)
    if not destination.exists() or destination.read_bytes() == source.read_bytes():
        raise ValueError('JPEXS did not produce a localized progress bar')
    run('-format', 'text:formatted', '-export', 'text', verified, destination)
    verified_text = (verified / '2.txt').read_text(encoding='utf8')
    if localized not in verified_text or 'ご注意' in verified_text:
        raise ValueError('Localized progress bar verification failed')
