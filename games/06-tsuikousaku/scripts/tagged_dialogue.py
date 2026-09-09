"""Compatibility entry point; the tagged codec belongs to the shared series layer."""
import sys
import pipeline as p
sys.path.insert(0,str(p.SERIES/'tools'))
import dialogue_tags as shared
from dialogue_tags import markup, decode
def layouts(commands,lookup):return shared.layouts(commands,lookup,shared.hard_breaks(p.WORK))
DOCUMENT=p.WORK/'work/dialogue-tagged.json'
def export_document(commands=None):return shared.document(p.WORK,commands)
def validate(commands=None):return shared.validate(p.WORK,commands)['units']
def import_document():return shared.import_document(p.WORK)
if __name__=='__main__':
    sys.argv.extend(['--game','kibu6']);shared.main()
