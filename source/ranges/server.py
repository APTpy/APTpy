import json, os, sys, secrets, threading, webbrowser, subprocess, tempfile, hashlib, shutil
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from range_formats import validate_ranges, selected_ions

ROOT=Path(__file__).parent

def atomic_write(path, raw):
    fd,tmp=tempfile.mkstemp(prefix='.'+path.name,dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as f:
            f.write(raw);f.flush();os.fsync(f.fileno())
        if path.exists():os.chmod(tmp,path.stat().st_mode)
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)

def encoded(data):return (json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode()
def spectrum_id(data):
    spectrum=data['spectrum_cache']
    return hashlib.sha256(json.dumps([[float(x) for x in spectrum[k]] for k in ('mass','counts')],separators=(',',':'),allow_nan=False).encode()).hexdigest()

class Project:
    def __init__(self):self.path=None;self.data=None;self.fingerprint=None
    def load(self,path):
        p=Path(path).expanduser().resolve();raw=p.read_bytes();d=json.loads(raw)
        s=d.get('spectrum_cache') or {}
        if not s.get('mass') or len(s['mass'])!=len(s.get('counts',[])):raise ValueError('This project has no valid cached spectrum.')
        notice='';sidecar=p.with_name(p.name+'.ranges-backup.json')
        if 'range_editor' not in d and sidecar.exists():
            backup=json.loads(sidecar.read_bytes())
            if backup.get('spectrum_sha256')==spectrum_id(d):
                validate_ranges(backup['range_editor']['ranges']);d['range_editor']=backup['range_editor']
                notice='Ranges restored from the independent range backup. Existing ion assignments were preserved; review them after candidate changes.'
            else:notice='A range backup exists for a different spectrum and was not restored.'
        if 'range_editor' in d and not sidecar.exists():
            validate_ranges(d['range_editor']['ranges'])
            atomic_write(sidecar,encoded({'format':'aptpy-independent-range-backup','version':1,'spectrum_sha256':spectrum_id(d),'range_editor':d['range_editor']}))
        self.path=p;self.data=d;self.fingerprint=hashlib.sha256(raw).hexdigest()
        return {'name':p.name,'path':str(p),'project':d,'notice':notice}
    def save(self,ranges,export_record=None):
        if not self.path:raise ValueError('Open a project first.')
        if hashlib.sha256(self.path.read_bytes()).hexdigest()!=self.fingerprint:raise ValueError('The project changed in another app. Reopen it before saving. Your current ranges remain visible.')
        validate_ranges(ranges)
        for r in ranges:
            if isinstance(r.get('ion_candidates'),list):
                r['ions']=selected_ions(r)
        backup=self.path.with_name(self.path.name+'.before-ranging.bak')
        if not backup.exists():shutil.copy2(self.path,backup)
        d=dict(self.data);d['range_editor']=dict(d.get('range_editor',{}));d['range_editor'].update({'version':1,'units':'Da/e','ranges':ranges})
        if export_record is not None:d['range_editor']['last_export']=export_record
        sidecar=self.path.with_name(self.path.name+'.ranges-backup.json')
        # Keep an independent latest-range copy even if the analyser rewrites the JSON.
        atomic_write(sidecar,encoded({'format':'aptpy-independent-range-backup','version':1,'spectrum_sha256':spectrum_id(d),'range_editor':d['range_editor']}))
        raw=encoded(d);atomic_write(self.path,raw)
        self.data=d;self.fingerprint=hashlib.sha256(raw).hexdigest()
        return {'saved':True,'backup':str(backup),'ranges_backup':str(sidecar)}

def main():
    project=Project();token=secrets.token_urlsafe(32);lock=threading.Lock()
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*a):pass
        def reply(self,status,obj):
            raw=json.dumps(obj,ensure_ascii=False).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
        def do_GET(self):
            if self.path.split('?')[0]!='/':self.send_error(404);return
            raw=(ROOT/'index.html').read_text().replace('__TOKEN__',token).encode();self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
        def do_POST(self):
            if self.headers.get('X-Editor-Token')!=token:self.reply(403,{'error':'Unauthorized'});return
            try:
                body=json.loads(self.rfile.read(int(self.headers.get('Content-Length',0))) or '{}')
                with lock:
                    if self.path=='/open':
                        path=body.get('path')
                        if not path:
                            result=subprocess.run(['osascript','-e','POSIX path of (choose file with prompt "Open an APT project JSON")'],capture_output=True,text=True)
                            if result.returncode:self.reply(200,{'cancelled':True});return
                            path=result.stdout.strip()
                        result=project.load(path)
                    elif self.path=='/save':result=project.save(body['ranges'])
                    else:raise ValueError('Unknown action')
                self.reply(200,result)
            except Exception as e:self.reply(400,{'error':str(e)})
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);url='http://127.0.0.1:%s/'%server.server_port
    print(url,flush=True)
    if '--no-browser' not in sys.argv:webbrowser.open(url)
    server.serve_forever()
if __name__=='__main__':main()
