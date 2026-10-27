"""Own module processes and report local URLs to the native host."""
import subprocess,sys,os,signal,json,threading,socket,time,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parent
children=[]
logs=Path.home()/'Library/Logs/APTpy';logs.mkdir(parents=True,exist_ok=True)
def emit(**data): print(json.dumps(data),flush=True)
def cleanup():
 for p in children:
  try: os.killpg(p.pid,signal.SIGTERM)
  except (ProcessLookupError, PermissionError): pass
def stop(*args):
 cleanup()
 raise SystemExit
signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
def start(index,folder,python):
 try:
  env=os.environ.copy();env['PYTHONUNBUFFERED']='1';env['PYTHONDONTWRITEBYTECODE']='1'
  if index==0:
   with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
   env['JUPYTER_PATH']=str(ROOT/'candidate/jupyter')
   command=[python,'-m','voila',str(ROOT/'candidate/1- APTpy-Spectrum Analyser-V1.0.2.ipynb'),'--no-browser','--Voila.ip=127.0.0.1',f'--port={port}','--Voila.port_retries=0']
   log=(logs/'candidate.log').open('a')
   p=subprocess.Popen(command,cwd=ROOT/folder,env=env,stdout=log,stderr=log,start_new_session=True);children.append(p)
   url=f'http://127.0.0.1:{port}/'
   for _ in range(240):
    if p.poll() is not None:raise RuntimeError('Candidate server stopped; see candidate.log')
    try:
     urllib.request.urlopen(url+'voila/templates/lab/static/aptpy-logo.png',timeout=1).close();break
    except Exception:time.sleep(.25)
   else:raise RuntimeError('Candidate server timed out')
  else:
   log=(logs/(folder+'.log')).open('a')
   p=subprocess.Popen([python,str(ROOT/folder/'server.py'),'--no-browser'],cwd=ROOT/folder,env=env,stdout=subprocess.PIPE,stderr=log,text=True,start_new_session=True);children.append(p)
   url=p.stdout.readline().strip()
   if not url.startswith('http://127.0.0.1:'):raise RuntimeError('Server failed to start; see '+folder+'.log')
  emit(index=index,url=url)
 except Exception as e:emit(index=index,error=str(e))
for i,folder in enumerate(['candidate','ranges','isotope']):
 python='/opt/anaconda3/envs/xrd_env/bin/python' if i==2 else '/opt/anaconda3/bin/python3'
 threading.Thread(target=start,args=(i,folder,python),daemon=True).start()
try:
 while True:time.sleep(1)
finally:cleanup()
