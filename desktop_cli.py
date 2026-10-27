"""Console entry point bundled alongside the desktop for external agents."""
import argparse
from pathlib import Path
import sys
import desktop_core as core


def main():
    if len(sys.argv)>1 and sys.argv[1]=='operator':
        sys.argv.pop(1)
        return core.op.main()
    p=argparse.ArgumentParser(description='GridCAD bounded deterministic rectangular core')
    sub=p.add_subparsers(dest='command',required=True)
    inspect=sub.add_parser('inspect');inspect.add_argument('--project',required=True);inspect.add_argument('--workbook',required=True)
    for name in ('propose','convert'):
        c=sub.add_parser(name);c.add_argument('--project',required=True);c.add_argument('--workbook',required=True)
        c.add_argument('--sheet',required=True);c.add_argument('--range',dest='selected_range',required=True)
        c.add_argument('--samples',required=True);c.add_argument('--labels',required=True,help='Exact unique label-container name')
        c.add_argument('--orientation',required=True,choices=list(core.ORIENTATIONS));c.add_argument('--transpose',action='store_true')
        c.add_argument('--confirm-current-formula-caches',action='store_true')
        if name=='convert':
            c.add_argument('--out-dir',required=True);c.add_argument('--review-notes',required=True)
            c.add_argument('--confirm-mapping',action='store_true',required=True)
            c.add_argument('--allow-unverified-material-profile',action='store_true',required=True)
    a=p.parse_args()
    try:
        project=core.load_project(a.project);book=core.read_workbook(a.workbook)
        if a.command=='inspect':
            result={'profile':core.PROFILE,'source_sha256':project['sha256'],
                    'workbook_sha256':core.op.digest(a.workbook),
                    'sheets':{k:{'stored_cells':len(v),'suggested_range':core.suggest_range(v)} for k,v in book.items()},
                    'sample_groups':{k:len(v) for k,v in project['groups'].items()},
                    'label_containers':{k:{'name':v['name'],'leaves':len(v['leaves'])} for k,v in project['containers'].items()},
                    'native_acceptance_verified':False}
        else:
            labels=[oid for oid,v in project['containers'].items() if v['name']==a.labels]
            if len(labels)!=1:core.op.fail('Label container name must identify exactly one container; inspect IDs or use the operator API for ambiguous names.')
            result=core.propose(project,a.workbook,book,a.sheet,a.selected_range,a.samples,labels[0],a.orientation,
                                transpose=a.transpose,cache_confirmed=a.confirm_current_formula_caches)
            if a.command=='convert':result=core.save(a.project,a.workbook,result,a.out_dir,a.review_notes)
        print(core.op.report_json(result));return 0
    except (core.op.ValidationError,OSError,ValueError,KeyError) as exc:
        print('Cannot complete: '+str(exc),file=sys.stderr);return 2


if __name__=='__main__':raise SystemExit(main())
