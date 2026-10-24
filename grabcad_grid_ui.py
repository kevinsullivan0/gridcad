"""Loopback-only review and explicitly unverified candidate-copy UI."""
from __future__ import annotations
import argparse
from decimal import Decimal, InvalidOperation
from http.server import BaseHTTPRequestHandler, HTTPServer
import copy
from pathlib import Path
import secrets
import tempfile
import webbrowser

from gridcad.core import ValidationError, read_workbook, inspect_project, json_text, strict_json, mapping_preview, file_hash, archive_inventory
from gridcad.geometry import inspect_geometry, propose_grid_mapping
from gridcad.candidate_writer import candidate_readiness, write_reviewed_candidate_copy, CHANNEL_RESINS

ROOT = Path(__file__).resolve().parent
LIMITS = {'workbook': 20 * 1024**2, 'project': 128 * 1024**2}
API_LIMIT = 64 * 1024

class ReviewServer(HTTPServer):
    allow_reuse_address = False
    def __init__(self, address=('127.0.0.1', 0)):
        if address[0] != '127.0.0.1':
            raise ValueError('Only IPv4 loopback binding is permitted.')
        super().__init__(address, Handler)
        self.token = secrets.token_urlsafe(32)
        self.origin = f'http://127.0.0.1:{self.server_port}'
        self.storage = tempfile.TemporaryDirectory(prefix='gridcad-review-')
        self.files = {}
        self.report = None
        self.analysis = None
        self.review = None
        self.downloads = {}
    def invalidate(self):
        self.report = self.analysis = self.review = None
        for path in self.downloads.values():
            path.unlink(missing_ok=True)
        self.downloads.clear()
    def server_close(self):
        super().server_close()
        if hasattr(self, 'storage'): self.storage.cleanup()

class Handler(BaseHTTPRequestHandler):
    server_version = 'GridCAD'
    def log_message(self, *args): pass  # No names, recipes, or tokens in access logs.
    def setup(self):
        super().setup()
        self.connection.settimeout(30)
    def reply(self, status, data, content_type='application/json'):
        if not isinstance(data, bytes): data = json_text(data).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Security-Policy', "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
        self.end_headers()
        self.wfile.write(data)
    def guard(self, api=False):
        if self.headers.get('Host') != self.server.origin.removeprefix('http://'):
            self.reply(403, {'error':'Unexpected host.'}); return False
        origin = self.headers.get('Origin')
        if origin is not None and origin != self.server.origin:
            self.reply(403, {'error':'Cross-origin requests are not allowed.'}); return False
        if self.headers.get('Sec-Fetch-Site') not in (None, 'same-origin', 'none'):
            self.reply(403, {'error':'Cross-site requests are not allowed.'}); return False
        if api and not secrets.compare_digest(self.headers.get('X-GridCAD-Token',''), self.server.token):
            self.reply(403, {'error':'Session expired or missing. Reopen the launcher link.'}); return False
        return True
    def do_GET(self):
        if not self.guard(): return
        if self.path.startswith('/api/download/'):
            if not self.guard(api=True): return
            path = self.server.downloads.get(self.path.removeprefix('/api/download/'))
            if path is None:
                self.reply(404, {'error':'Download expired. Review and save again.'}); return
            self.reply(200, path.read_bytes(), 'application/octet-stream'); return
        assets = {'/':('index.html','text/html; charset=utf-8'), '/app.js':('app.js','text/javascript; charset=utf-8'), '/style.css':('style.css','text/css; charset=utf-8')}
        item = assets.get(self.path)
        if item is None: self.reply(404, {'error':'Not found.'}); return
        self.reply(200, (ROOT/'ui'/item[0]).read_bytes(), item[1])
    def body(self, limit):
        if self.headers.get('Transfer-Encoding') or len(self.headers.get_all('Content-Length', [])) != 1:
            raise ValidationError('One explicit Content-Length is required; streaming transfer encoding is not supported.')
        try: n = int(self.headers['Content-Length'])
        except (ValueError, TypeError): raise ValidationError('Invalid request length.')
        if not 0 < n <= limit: raise ValidationError(f'Request exceeds limit ({limit // 1024} KiB) or is empty.')
        data = self.rfile.read(n)
        if len(data) != n: raise ValidationError('Upload was interrupted. Select the file again.')
        return data
    def do_POST(self):
        if not self.guard(api=True): return
        try:
            if self.path in ('/api/analyze','/api/preview','/api/invalidate','/api/revoke-review') or self.path.startswith('/api/upload/'):
                self.server.review = None
            if self.path.startswith('/api/upload/'):
                kind = self.path.removeprefix('/api/upload/')
                if kind not in LIMITS: raise ValidationError('Unknown input kind.')
                if self.headers.get('Content-Type') != 'application/octet-stream': raise ValidationError('Binary upload required.')
                self.server.invalidate()
                data = self.body(LIMITS[kind])
                # Browser-supplied paths/names are NEVER used as filesystem paths.
                path = Path(self.server.storage.name) / ('workbook.xlsx' if kind=='workbook' else 'project.print')
                path.write_bytes(data)
                self.server.files[kind] = path
                info = read_workbook(path, metadata_only=True) if kind == 'workbook' else None
                self.reply(200, {'bytes':len(data), 'source_modified':False, 'workbook_info':info}); return
            if self.headers.get('Content-Type') != 'application/json': raise ValidationError('JSON content type required.')
            options = strict_json(self.body(API_LIMIT))
            if not isinstance(options, dict): raise ValidationError('Expected an options object.')
            if self.path == '/api/revoke-review':
                self.reply(200, {'revoked':True}); return
            if self.path == '/api/invalidate':
                self.server.invalidate()
                self.reply(200, {'invalidated':True}); return
            if self.path == '/api/workbook-preview':
                if set(options) - {'sheet','start_cell'}: raise ValidationError('Unexpected workbook preview options.')
                if 'workbook' not in self.server.files: raise ValidationError('Choose a workbook first.')
                if not options.get('sheet'): raise ValidationError('Choose an Excel tab first.')
                self.reply(200, read_workbook(self.server.files['workbook'], metadata_only=True, sheet=options['sheet'], cell_range=options.get('start_cell') or 'A1')); return
            if self.path == '/api/analyze':
                self.server.invalidate()
                if set(options)-{'sheet','range','order','delimiter','empty_zero','formula_cache_confirmed','transpose','tray_id','selection'}:
                    raise ValidationError('Unexpected analysis options. Use the visible workbook and geometry controls.')
                if set(self.server.files) != {'workbook','project'}: raise ValidationError('Choose both files first.')
                if type(options.get('transpose', False)) is not bool: raise ValidationError('Transpose must be an explicit on/off choice.')
                if not options.get('range'):
                    raise ValidationError('Enter the recipe grid rectangle, for example B2:F4. Exclude Excel headers and sidebar inputs, but keep blank positions inside the grid.')
                grid = read_workbook(self.server.files['workbook'], sheet=options.get('sheet') or None,
                    cell_range=options.get('range') or None, order=options.get('order','CMYKWT'),
                    delimiter=options.get('delimiter','auto'), empty_channels_zero=options.get('empty_zero') is True,
                    formula_cache_confirmed=options.get('formula_cache_confirmed') is True, tolerance=Decimal(0))
                project = inspect_project(self.server.files['project'])
                gate = candidate_readiness(self.server.files['project'])
                stored = archive_inventory(self.server.files['project'])['project_document']['project']
                profile_snapshot = {'gender':stored.get('gender'), 'selectedPrinter':stored.get('selectedPrinter'), 'trays':[]}
                for tray in stored.get('trays',[]):
                    params = tray.get('pluginParameters') or {}
                    profile_snapshot['trays'].append({'id':tray.get('id'), **{key:params.get(key) for key in ('pj.tray.printMode','pj.tray.printOnFabric','pj.tray.jobTypeId','pj.tray.resins','pj.tray.supportResins','pj.tray.adhesionLayer','pj.tray.AdhesiveCarpetMaterial','pj.tray.AdhesiveCarpetThickness')}})
                result = {'grid':grid, 'project':project, 'writer_enabled':gate['candidate_allowed'], 'profile_gate':gate, 'stored_profile':profile_snapshot, 'geometry':None, 'proposal':None, 'analysis_id':secrets.token_urlsafe(24)}
                # Read-only geometry can fail while the recipe and material inventory remain useful.
                try:
                    result['geometry'] = inspect_geometry(self.server.files['project'], tray_id=options.get('tray_id') or None)
                    result['proposal'] = propose_grid_mapping(grid, self.server.files['project'], selection=options.get('selection'), tray_id=options.get('tray_id') or None)
                except ValidationError as exc: result['geometry_error'] = str(exc)
                if result.get('proposal'):
                    proposal = result['proposal']
                    proposal['orientation_candidates'] = [c for c in proposal['orientation_candidates'] if c['transform']['transpose'] is options.get('transpose', False)]
                    if not proposal['orientation_candidates']:
                        proposal['issues'].append('No orientation matches the selected transpose setting. Check the recipe rectangle, sample region and transpose choice; no alternative is selected automatically.')
                result['transpose'] = options.get('transpose', False)
                self.server.analysis = {'id':result['analysis_id'], 'options':copy.deepcopy(options), 'hashes':{k:file_hash(v) for k,v in self.server.files.items()}}
                self.server.report = result
                self.reply(200,result); return
            if self.path in ('/api/preview','/api/save'):
                report, analysis = self.server.report, self.server.analysis
                if report is None or analysis is None or options.get('analysis_id') != analysis['id']:
                    raise ValidationError('Inspection expired. Inspect both inputs again.')
                if {k:file_hash(v) for k,v in self.server.files.items()} != analysis['hashes']:
                    self.server.invalidate()
                    raise ValidationError('Input changed. Inspect and confirm the refreshed mapping.')
                if self.path == '/api/save':
                    review = self.server.review
                    self.server.review = None  # Every save attempt consumes its one-use review.
                    if review is None or options != {'analysis_id':analysis['id'], 'review_id':review['id']}:
                        raise ValidationError('Review expired or already used. Preview again before saving.')
                    output = Path(self.server.storage.name) / (secrets.token_hex(16)+'.PRINT')
                    try:
                        result = write_reviewed_candidate_copy(report['grid'], self.server.files['project'], output,
                            selection=analysis['options'].get('selection',{}), candidate_id=review['candidate_id'],
                            assignment_policy={'mode':'overwrite_targets'}, reviewed=True)
                    except Exception:
                        # Even a post-publication reporting failure must not leave
                        # an inaccessible output behind or create a retry ambiguity.
                        output.unlink(missing_ok=True)
                        raise
                    download_id = secrets.token_urlsafe(32)
                    self.server.downloads[download_id] = output
                    result.pop('output',None)
                    self.reply(200, {'result':result, 'download_id':download_id, 'filename':'GridCAD-unverified-candidate.PRINT'}); return
                self.server.review = None
                if set(options) != {'analysis_id','candidate_id','reviewed','overwrite_targets'}:
                    raise ValidationError('Unexpected preview options. Refresh the interface.')
                if options['reviewed'] is not True or options['overwrite_targets'] is not True:
                    raise ValidationError('Confirm orientation, complete role regions and replacement of selected materials first.')
                proposal = report.get('proposal')
                candidate = next((x for x in (proposal or {}).get('orientation_candidates',[]) if x['candidate_id']==options['candidate_id']),None)
                if candidate is None: raise ValidationError('Choose one of the current orientation candidates.')
                config = {'schema':'gridcad.mapping.v1', 'mapping_confirmed':True, 'tray_id':proposal['tray_id'],
                    'transform':candidate['transform'], 'targets':candidate['targets'], 'channel_resin_ids':CHANNEL_RESINS.copy(),
                    'label_material':{'mode':'base_material','name':'VEcoFlxBlk','vendor_material_id':'VEcoFlxBlk','resin_id':'11936'}}
                preview = mapping_preview(report['grid'],self.server.files['project'],config)
                result = None
                review_id = None
                if report['profile_gate']['candidate_allowed']:
                    # Prepare and audit a private disposable copy to establish exact changes,
                    # numeric admission and preservation BEFORE offering a downloadable copy.
                    trial = Path(self.server.storage.name) / (secrets.token_hex(16)+'.preview')
                    try:
                        result = write_reviewed_candidate_copy(report['grid'],self.server.files['project'],trial,
                            selection=analysis['options'].get('selection',{}),candidate_id=candidate['candidate_id'],
                            assignment_policy={'mode':'overwrite_targets'},reviewed=True)
                    finally:
                        trial.unlink(missing_ok=True)
                    result.pop('output',None)
                    review_id = secrets.token_urlsafe(24)
                    self.server.review = {'id':review_id,'candidate_id':candidate['candidate_id']}
                self.reply(200, {'preview':preview,'result':result,'review_id':review_id,
                                 'writer_enabled':review_id is not None,'profile_gate':report['profile_gate']}); return
            self.reply(404, {'error':'No such operation.'})
        except (ValidationError, InvalidOperation, ValueError, TypeError, KeyError, OSError) as exc:
            self.server.review = None
            self.reply(400, {'error':str(exc)[:1000], 'source_modified':False})


def main():
    p=argparse.ArgumentParser(description='Local GridCAD candidate-copy review. Original files are never changed.')
    p.add_argument('--no-browser', action='store_true')
    args=p.parse_args()
    with ReviewServer() as server:
        url=server.origin+'/#'+server.token
        print('GridCAD unverified candidate copies. No printer connection or print jobs.\n'+url+'\nKeep this terminal open. Ctrl+C stops and removes temporary uploads.',flush=True)
        if not args.no_browser: webbrowser.open(url)
        try: server.serve_forever()
        except KeyboardInterrupt: pass

if __name__=='__main__': main()
