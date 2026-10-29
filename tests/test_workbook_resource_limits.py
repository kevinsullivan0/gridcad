"""Small generated controls exercise input ceilings without allocating hostile sizes."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from contextlib import nullcontext

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'operator'))
from gridcad_operator import operator as op
import diagnostics

M = op.NS['m']
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'

class WorkbookLimits(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'input.xlsx'
    def tearDown(self): self.tmp.cleanup()
    def write(self, *, tabs=None, rels=None, sheets=None, strings=None, encoding='utf-8'):
        tabs = tabs if tabs is not None else [('Recipes','1','r1')]
        rels = rels if rels is not None else [('r1','worksheets/sheet1.xml')]
        sheets = sheets if sheets is not None else {'xl/worksheets/sheet1.xml':'<row><c r="A1" t="inlineStr"><is><t>Grüße 中文</t></is></c><c r="B1"><f>1+1</f><v>2</v></c></row>'}
        parts = {
            'xl/workbook.xml':f'<workbook xmlns="{M}" xmlns:r="{R}"><sheets>'+''.join(f'<sheet name="{n}" sheetId="{i}" r:id="{r}"/>' for n,i,r in tabs)+'</sheets></workbook>',
            'xl/_rels/workbook.xml.rels':'<Relationships>'+''.join(f'<Relationship Id="{i}" Target="{t}"/>' for i,t in rels)+'</Relationships>',
        }
        parts.update({n:f'<worksheet xmlns="{M}"><sheetData>{c}</sheetData></worksheet>' for n,c in sheets.items()})
        if strings is not None: parts['xl/sharedStrings.xml']=f'<sst xmlns="{M}">'+''.join('<si><t>'+t+'</t></si>' for t in strings)+'</sst>'
        with zipfile.ZipFile(self.path,'w',zipfile.ZIP_DEFLATED) as z:
            for name,text in parts.items(): z.writestr(name, ('<?xml version="1.0" encoding="'+encoding.replace('-le','le').replace('-be','be')+'"?>'+text).encode(encoding))
        return parts
    def reject(self, token='Resource limit:', **limits):
        with (patch.multiple(op, **limits) if limits else nullcontext()), self.assertRaisesRegex(op.ValidationError,token): op.workbook(self.path)
    def test_normal_encodings_formula_and_selected(self):
        for encoding in ('utf-8','utf-16','utf-16-le','utf-16-be'):
            self.write(encoding=encoding)
            book=op.workbook(self.path)
            self.assertEqual(book['Recipes']['A1']['value'],'Grüße 中文')
            self.assertTrue(book['Recipes']['B1']['formula'])
            self.assertEqual(book,op.workbook(self.path,'Recipes'))
    def test_doctype_entities_rejected_encoding_independently(self):
        for encoding in ('utf-8','utf-16','utf-16-le','utf-16-be'):
            for decl in ('<!DOCTYPE x [<!ENTITY a "hello">]>', '<!DOCTYPE x SYSTEM "file:///not-read">', '<!DOCTYPE x PUBLIC "id" "https://invalid.example/">'):
                raw=('<?xml version="1.0" encoding="'+encoding.replace('-le','le').replace('-be','be')+'"?>'+decl+'<x/>').encode(encoding)
                with self.assertRaisesRegex(op.ValidationError,'DTD/entities'): op.xml(raw)
        with self.assertRaises(op.ValidationError): op.xml(b'<unclosed>')
    def test_archive_and_part_reject_before_xml(self):
        self.write()
        for limits in ({'WORKBOOK_BYTES':1},{'WORKBOOK_PART_BYTES':1}):
            with patch.multiple(op,**limits), patch.object(op,'xml',side_effect=AssertionError('must not parse')):
                with self.assertRaisesRegex(op.ValidationError,'Resource limit:'): op.workbook(self.path)
    def test_cells_exact_boundary_and_sparse_address(self):
        self.write(sheets={'xl/worksheets/sheet1.xml':'<row><c r="A1"><v>1</v></c><c r="XFD1048576"><v>2</v></c></row>'})
        with patch.object(op,'WORKBOOK_CELLS',2): self.assertEqual(len(op.workbook(self.path)['Recipes']),2)
        self.reject(WORKBOOK_CELLS=1)
    def test_aggregate_cells_across_sheets(self):
        self.write(tabs=[('One','1','r1'),('Two','2','r2')],rels=[('r1','worksheets/one.xml'),('r2','worksheets/two.xml')],sheets={f'xl/worksheets/{n}.xml':'<row><c r="A1"><v>1</v></c></row>' for n in ('one','two')})
        self.reject(WORKBOOK_CELLS=1)
        with patch.object(op,'WORKBOOK_CELLS',1): self.assertEqual(len(op.workbook(self.path,'One')['One']),1)
    def test_shared_strings_and_repeated_value_text(self):
        self.write(strings=['abcd','efgh'],sheets={'xl/worksheets/sheet1.xml':'<row><c r="A1" t="s"><v>0</v></c><c r="B1" t="s"><v>1</v></c></row>'})
        with patch.object(op,'WORKBOOK_STRINGS',2): self.assertEqual(op.workbook(self.path)['Recipes']['B1']['value'],'efgh')
        self.reject(WORKBOOK_STRINGS=1)
        # A repeated shared-string value is charged per resulting cell even
        # though the Python strings may share an object internally.
        self.write(strings=['x'*100],sheets={'xl/worksheets/sheet1.xml':'<row>'+''.join(f'<c r="A{i}" t="s"><v>0</v></c>' for i in range(1,11))+'</row>'})
        self.reject(WORKBOOK_TEXT=700)
    def test_parser_counts_depth_nodes_text_during_construction(self):
        for raw,limit in [(b'<x><y/></x>',{'WORKBOOK_XML_DEPTH':1}),(b'<x><y/></x>',{'WORKBOOK_XML_NODES':1}),(b'<x>ab</x>',{'WORKBOOK_TEXT':1}),(b'<x a="ab"/>',{'WORKBOOK_TEXT':1})]:
            with patch.multiple(op,**limit),self.assertRaisesRegex(op.ValidationError,'Resource limit:'):op.xml(raw)
        with patch.object(op,'WORKBOOK_CELLS',1),self.assertRaisesRegex(op.ValidationError,'stored cells'):op.xml(f'<x xmlns="{M}"><c/><c/></x>'.encode())
    def test_namespace_expanded_names_charge_before_tree_growth(self):
        uri='u'*1000
        raw=('<r xmlns:p="'+uri+'">'+''.join(f'<p:n{i}/>' for i in range(10))+'</r>').encode()
        budget={'nodes':0,'text':0}
        with patch.object(op,'WORKBOOK_TEXT',3000), self.assertRaisesRegex(op.ValidationError,'Resource limit:'):
            op.xml(raw,budget)
        self.assertLessEqual(budget['nodes'],4)
        # Normal namespace use remains accepted at its exact expanded charge.
        raw=b'<r xmlns:p="urn:short"><p:x/></r>'
        with patch.object(op,'WORKBOOK_TEXT',13): self.assertEqual(op.xml(raw)[0].tag,'{urn:short}x')

    def test_namespace_attribute_amplification_refused_before_tree_parse(self):
        for raw in [('<r xmlns:p="'+('u'*1025)+'" p:a=""/>').encode(),
                    ('<r xmlns:p="urn:short" '+''.join(f'p:a{i}="" ' for i in range(129))+'/>').encode()]:
            with patch.object(op.ET,'fromstring',side_effect=AssertionError('must refuse before expansion')):
                with self.assertRaisesRegex(op.ValidationError,'Resource limit:'): op.xml(raw)
        raw=('<r xmlns:p="'+('u'*1024)+'" p:a=""/>').encode()
        self.assertEqual(len(op.xml(raw).attrib),1)

    def test_resource_like_private_exception_not_copied_to_report(self):
        sentinel='SENTINEL_PRIVATE_CONTENT'
        try: op.read_json('{"resource limit: '+sentinel+'":1,"resource limit: '+sentinel+'":2}')
        except op.ValidationError as exc:
            d=diagnostics.describe(exc)
            self.assertNotEqual(d.code,'GCD206')
            path=diagnostics.create_report(exc,d,directory=Path(self.tmp.name)/'report')
            self.assertNotIn(sentinel,path.read_text())
        else: self.fail('duplicate JSON key was accepted')

    def test_duplicate_metadata_and_targets_before_selected_filter(self):
        cases=[
            ([('One','1','r1'),('One','2','r2')],[('r1','worksheets/a.xml'),('r2','worksheets/b.xml')]),
            ([('One','1','r1'),('Two','1','r2')],[('r1','worksheets/a.xml'),('r2','worksheets/b.xml')]),
            ([('One','1','r1')],[('r1','worksheets/a.xml'),('r1','worksheets/b.xml')]),
            ([('One','1','r1'),('Two','2','r2')],[('r1','worksheets/a.xml'),('r2','/xl/worksheets/./a.xml')]),
        ]
        for tabs,rels in cases:
            self.write(tabs=tabs,rels=rels)
            for selected in (None,'One'):
                with self.assertRaisesRegex(op.ValidationError,'[Dd]uplicate'):op.workbook(self.path,selected)
    def test_sheet_count_and_invalid_string_reference(self):
        self.write();self.reject(WORKBOOK_SHEETS=0)
        for value in ('-1','100','bad'):
            self.write(strings=['ok'],sheets={'xl/worksheets/sheet1.xml':f'<row><c r="A1" t="s"><v>{value}</v></c></row>'})
            self.reject('shared-string reference')
    def test_plain_language_diagnostic(self):
        d=diagnostics.describe(op.ValidationError('Resource limit: workbook exceeds 64 MiB expanded. Use a smaller values-only workbook.'))
        self.assertEqual(d.code,'GCD206');self.assertIn('64 MiB',d.text());self.assertIn('smaller',d.remedy)

if __name__=='__main__':unittest.main()
