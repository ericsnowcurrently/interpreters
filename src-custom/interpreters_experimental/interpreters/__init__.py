import sys

# We pull this in for channels.py
from interpreters_backport.interpreters import _crossinterp
sys.modules[f'{__name__}._crossinterp'] = _crossinterp
