"""Compare isolated baseline/candidate processes on invented, non-printable inputs.

Run with --baseline CHECKOUT --candidate CHECKOUT --output NEW_FOLDER.
No private inputs, network, native GrabCAD, or installed app are used.
Peak RSS is available on Linux/macOS; timings are wall-clock seconds.
"""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import struct
import subprocess
import sys
import time
import zipfile


def worker(repo, case, inputs, output):
    sys.path.insert(0, str(repo))
    import desktop_core as core
    times, cpu_times = {}, {}
    def measure(name, fn):
        start = time.perf_counter()
        cpu_start = time.process_time()
        value = fn()
        times[name] = time.perf_counter() - start
        cpu_times[name] = time.process_time() - cpu_start
        return value
    if case == 'mesh':
        raw = (inputs/'mesh.stl').read_bytes()
        result = measure('mesh', lambda: core._mesh(raw))
        identity = {'bounds': result['bounds'], 'triangles': result['triangles'],
                    'mesh_sha256': result['sha256'], 'top_length': len(result['top']),
                    'top_sha256': hashlib.sha256(result['top'].tobytes()).hexdigest()}
    elif case == 'skinny-grid':
        records = [{'id': str(i), 'bounds': [[i*12-4,-4,0],[i*12+4,4,2]],
                    'center': [i*12,0,1]} for i in range(5000)]
        result = measure('shape_grid', lambda: core._shape_grid(records, {}))
        identity = {'result_sha256': hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()}
    else:
        folder = inputs/case
        project_path, workbook_path = folder/'DO_NOT_PRINT.PRINT', folder/'DO_NOT_PRINT.xlsx'
        rows, columns = (33,21) if case == 'mixed-grid' else (4,6)
        project = measure('load_project', lambda: core.load_project(project_path))
        book = measure('workbook', lambda: core.read_workbook(workbook_path))
        reference = sorted(project['containers']['synthetic-labels']['leaves'])[0]
        proposal = measure('propose', lambda: core.propose(project, workbook_path, book,
            'Recipes', 'D4:'+core.address(rows+3,columns+3), 'Sample', 'synthetic-labels',
            'Rows down; columns right', label_mode='reference', label_reference=reference))
        audit = measure('save', lambda: core.save(project_path, workbook_path, proposal,
            output, 'Synthetic known indices reviewed for regression.'))
        identity = {'candidate_sha256': audit['output_sha256'], 'mapping_sha256': audit['mapping_sha256']}
    try:
        import resource
        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        peak_bytes = peak if sys.platform == 'darwin' else peak*1024
    except ImportError:
        peak_bytes = None
    print(json.dumps({'seconds': times, 'cpu_seconds': cpu_times, 'peak_rss_bytes': peak_bytes, 'identity': identity}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path)
    parser.add_argument('--candidate', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--repeats', type=int, default=3)
    parser.add_argument('--worker', choices=('mixed-grid','large-payload','mesh','skinny-grid'))
    parser.add_argument('--inputs', type=Path)
    args = parser.parse_args()
    if args.worker:
        worker(args.candidate, args.worker, args.inputs, args.output)
        return
    if not args.baseline or not args.candidate or args.repeats < 1:
        parser.error('Provide both checkouts and a positive repeat count.')
    args.output.mkdir()  # Exclusive: do not overwrite benchmark evidence.
    inputs = args.output/'inputs'; inputs.mkdir()
    sys.path.insert(0, str(args.baseline.resolve()))
    from tools.make_desktop_examples import create
    create(inputs/'mixed-grid', rows=33, columns=21, sample_shape='mixed')
    create(inputs/'large-payload')
    with zipfile.ZipFile(inputs/'large-payload/DO_NOT_PRINT.PRINT', 'a', compression=zipfile.ZIP_DEFLATED) as archive:
        with archive.open('opaque/large.dat', 'w') as member:
            for _ in range(64):
                member.write(bytes(range(256))*4096)
    with (inputs/'mesh.stl').open('wb') as mesh:
        mesh.write(bytes(80)+struct.pack('<I',600000))
        bottom = struct.pack('<12fH',0,0,-1,0,0,0,1,0,0,0,1,0,0)
        top = struct.pack('<12fH',0,0,1,0,0,2,1,0,2,0,1,2,0)
        for _ in range(600):
            mesh.write((bottom+top)*500)
    results = {'platform': platform.platform(), 'python': sys.version, 'repeats': args.repeats, 'cases': {}}
    for case in ('mixed-grid','large-payload','mesh','skinny-grid'):
        samples = {'baseline': [], 'candidate': []}
        # Alternate variants to reduce systematic run-order effects.
        for repeat in range(args.repeats):
            for variant, repo in (('baseline',args.baseline),('candidate',args.candidate)):
                destination = args.output/f'{case}-{variant}-{repeat}'
                raw = subprocess.check_output([sys.executable,str(Path(__file__).resolve()),
                    '--worker',case,'--candidate',str(repo.resolve()),'--inputs',str(inputs.resolve()),
                    '--output',str(destination.resolve())], text=True)
                samples[variant].append(json.loads(raw))
        identities = [r['identity'] for group in samples.values() for r in group]
        if any(identity != identities[0] for identity in identities):
            raise RuntimeError(f'{case}: baseline/candidate outputs differ')
        results['cases'][case] = samples
        (args.output/'results.json').write_text(json.dumps(results, indent=2)+'\n')
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
