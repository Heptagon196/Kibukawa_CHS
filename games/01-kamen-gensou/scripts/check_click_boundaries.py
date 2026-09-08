"""Compatibility entry point; implementation belongs to the shared series layer."""
import sys
import pipeline as p
sys.path.insert(0,str(p.SERIES/'tools'))
from click_boundaries import units, validate as shared_validate

def validate(commands):
    return shared_validate(commands,p.WORK)
