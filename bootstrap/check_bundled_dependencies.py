"""Portable dependency smoke test. With Linux Python this is NOT a Windows test."""
import io
from pathlib import Path
import sys

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root / 'runtime' / 'site-packages'))
import openpyxl
import et_xmlfile
import defusedxml
from defusedxml.common import EntitiesForbidden
from openpyxl.xml.functions import fromstring

assert (openpyxl.__version__, et_xmlfile.__version__, defusedxml.__version__) == ('3.1.5','2.0.0','0.7.1')
assert openpyxl.DEFUSEDXML
try:
    fromstring(b'<!DOCTYPE x [<!ENTITY payload "BAD">]><x>&payload;</x>')
except EntitiesForbidden:
    pass
else:
    raise AssertionError('XML entity expansion was not blocked')
w = openpyxl.Workbook()
w.active['A1'] = '1/2/3/4/5/85'
b = io.BytesIO()
w.save(b)
b.seek(0)
assert openpyxl.load_workbook(b).active['A1'].value == '1/2/3/4/5/85'
print('Bundled dependencies: pinned versions, XLSX round-trip, and XML entity blocking passed.')
print('Interpreter actually used:', sys.executable, sys.version)
