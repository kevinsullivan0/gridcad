import argparse
from decimal import Decimal
from pathlib import Path
import sys
from .core import *

def write_new(path,text):
    with Path(path).open('x',encoding='utf-8') as f: f.write(text+'\n')

def main():
    ap=argparse.ArgumentParser(description='Read-only Excel grid / GrabCAD project inspection. No project writer.')
    sub=ap.add_subparsers(dest='command',required=True)
    for name in ('grid','preview'):
        p=sub.add_parser(name);p.add_argument('workbook');p.add_argument('--sheet');p.add_argument('--range',dest='cell_range')
        p.add_argument('--order',default='CMYKWT');p.add_argument('--delimiter',choices=['auto','slash','comma','semicolon','space'],default='auto')
        p.add_argument('--empty-channels-zero',action='store_true');p.add_argument('--sum-tolerance',type=Decimal,default=Decimal(0))
        p.add_argument('--out',required=True)
        if name=='preview':p.add_argument('project');p.add_argument('--mapping',required=True);p.add_argument('--html')
    p=sub.add_parser('inspect');p.add_argument('project');p.add_argument('--out',required=True)
    p=sub.add_parser('audit');p.add_argument('before');p.add_argument('after');p.add_argument('--out',required=True)
    a=ap.parse_args()
    try:
        if getattr(a,'html',None) and Path(a.html).resolve()==Path(a.out).resolve():
            raise ValidationError('JSON and HTML outputs must be different paths.')
        # Reports cannot overwrite any input or any existing file, including symlinks.
        for dest in [a.out]+([a.html] if getattr(a,'html',None) else []):
            if Path(dest).exists() or Path(dest).is_symlink():raise ValidationError(f'Output already exists: {dest}; choose a new report path.')
        if a.command in ('grid','preview'):
            grid=read_workbook(a.workbook,sheet=a.sheet,cell_range=a.cell_range,order=a.order,delimiter=a.delimiter,
                               empty_channels_zero=a.empty_channels_zero,tolerance=a.sum_tolerance)
            report=grid if a.command=='grid' else mapping_preview(grid,a.project,strict_json(Path(a.mapping).read_bytes()))
        elif a.command=='inspect':report=inspect_project(a.project)
        else:report=audit_projects(a.before,a.after)
        write_new(a.out,json_text(report))
        if getattr(a,'html',None):write_new(a.html,render_preview(report))
        print(f'Read-only report saved: {a.out}. No project changed.')
        return 2 if report.get('issues') or report.get('errors') else 0
    except (ValidationError,OSError,ValueError,KeyError,zipfile.BadZipFile) as exc:
        print(f'Cannot complete: {exc}',file=sys.stderr);return 2
if __name__=='__main__':sys.exit(main())
