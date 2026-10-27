import json,secrets,subprocess,webbrowser,tempfile,os,sys,math
from pathlib import Path
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
ROOT=Path(__file__).parent
sys.path.insert(0,str(ROOT))
from apt_isotope_overlap import analyse, components, formula_text
from compose_project import composition_tables
def json_safe(value):
 if isinstance(value,float) and (math.isnan(value) or math.isinf(value)): return None
 if isinstance(value,dict): return {k:json_safe(v) for k,v in value.items()}
 if isinstance(value,list): return [json_safe(v) for v in value]
 return value
def explain_peak(peak):
 windows=peak['related_windows'];selected=next(w for w in windows if w['range_number']==peak['range_number'])
 names=[c['ion'] for c in selected['contributions'] if c['isotope_probability']>0]
 terms=[f"{c['isotope_probability']:.6g} × total {c['ion']}" for c in selected['contributions'] if c['isotope_probability']>0]
 evidence=[]
 for c in selected['contributions']:
  if c['isotope_probability']<=0:continue
  support=[w for w in windows if w['range_number']!=peak['range_number'] and any(x['ion']==c['ion'] and x['isotope_probability']>0 for x in w['contributions'])]
  exclusive=[w['range_number'] for w in support if sum(x['isotope_probability']>0 for x in w['contributions'])==1]
  text=(f"{c['ion']}: this window captures {100*c['isotope_probability']:.4f}% of its full natural isotope pattern. ")
  if support:
   text+='Other constraining windows: '+', '.join('R'+str(w['range_number']) for w in support)+'. '
   text+=('Windows assigned only to this species in the current model: '+', '.join('R'+str(n) for n in exclusive)+'. ') if exclusive else 'All other supporting windows are also shared in this model. '
  else:text+='There is no other supporting isotope window in this fitted group. Its contribution is inferred from the remainder after fitting the other candidates; this is not independent confirmation of this ion. '
  evidence.append(text)
 worst=sorted([w for w in windows if w['pearson_residual'] is not None and math.isfinite(w['pearson_residual'])],key=lambda w:abs(w['pearson_residual']),reverse=True)[:3]
 status=peak['diagnostic']['status']
 if status=='model_misfit':decision='The group fails the isotope-pattern agreement check. Review the largest discrepancies below, candidate identities, range capture and background. A good match in this one range does not validate the split. Do not decide to remove an ion from its estimated share alone.'
 elif status=='no_redundant_check':decision='This group has no extra independent measurements for a fit check. The split depends on the assumed candidates and isotope ratios; seek additional isotope evidence before changing an assignment.'
 elif status=='not_identifiable':decision='These windows cannot uniquely separate the candidates. Additional independent isotope information or a justified constraint is needed; no split is reported.'
 else:decision='The group passes the current count-based agreement check. Inspect each ion’s supporting windows and uncertainties before changing its selection. Agreement supports this model but does not prove every candidate identity.'
 return {'steps':[
  f"1. Count the signal: Range {peak['range_number']} spans {peak['lower_mz']:.4f}–{peak['upper_mz']:.4f} Da/e and contains {peak['observed_ions']:.0f} counts. Selected candidates: {', '.join(names)}.",
  '2. Link isotope windows: fit '+', '.join('R'+str(w['range_number']) for w in windows)+f" together, with {peak['diagnostic']['species']} ion species. An overlap in another window can connect further species to this group.",
  '3. Build the equation for this range: expected counts = '+' + '.join(terms)+' + background. Each total means the fitted amount across that species’ full isotope pattern, not just this range.',
  '4. Fit all these equations together using nonnegative Poisson maximum likelihood. Multiply each fitted species total by its isotope probability in this window, then divide by the total fitted signal to obtain the reported shares.',
  '5. Check the whole group: '+decision], 'ion_evidence':evidence,
  'largest_discrepancies':[{'range_number':w['range_number'],'observed_ions':w['observed_ions'],'fitted_total_ions':w['fitted_total_ions'],'observed_minus_fitted':w['observed_ions']-w['fitted_total_ions'],'pearson_residual':w['pearson_residual']} for w in worst],
  'comparison_advice':'For a doubtful candidate, save an alternative candidate selection, rerun and compare the same isotope windows. More candidates can improve a fit simply by adding flexibility, so fit improvement alone does not establish an ion’s identity.'}
def peak_details(result):
 model=result['model'];A=model['A'];fits=result['range_fit'].to_dict('records')
 shares=result['shares'].to_dict('records');totals=result['species_fit'].to_dict('records')
 details=[]
 for group,(rr,cc) in enumerate(components(A),1):
  diagnostic=next(g for g in result['group_diagnostics'].to_dict('records') if g['group']==group)
  windows=[]
  for k in rr:
   contributions=[]
   for j in cc:
    ion=model['species'][j];formula=formula_text(ion['formula'])
    total=next((s for s in totals if s['group']==group and s['formula']==formula and s['charge']==ion['charge']),None)
    contributions.append({'ion':ion['ion_label'],'isotope_probability':float(A[k,j]),'fitted_signal_ions':float(A[k,j])*total['fitted_full_pattern_ions'] if total else None})
   windows.append({**fits[k],'contributions':contributions})
  for k in rr:
   if fits[k]['checked_species']<2:continue
   details.append({**fits[k],'group':group,'diagnostic':diagnostic,
    'contributions':[s for s in shares if s['range_number']==k+1],
    'related_windows':windows,
    'method':{'name':'Nonnegative Poisson maximum likelihood','equation':'Expected range counts = sum(isotope probability × fitted ion total) + background',
     'background':'No background correction supplied (zero assumed).',
     'uncertainty':'95% parametric bootstrap interval, 200 repeats; counting variation only.',
     'count_source':result['count_source'],
     'interpretation':'All connected isotope windows are fitted together. Signal share divides the fitted signal; allocated counts divide the observed counts using those fitted fractions. Contributions are estimates, not individual event identities.'}})
 details=json_safe(details)
 for peak in details:peak['walkthrough']=explain_peak(peak)
 return details
class App:
 def run(self,path):
  p=Path(path).expanduser().resolve(); project=json.loads(p.read_text())
  result=analyse(project,isotope_source='apav',bootstrap=200)
  ions=result['species_fit'].copy(); ions['ion_count']=ions['fitted_full_pattern_ions'].clip(lower=0)
  _,atoms=composition_tables(result)
  peaks=peak_details(result)
  epos=Path(project.get('epos_file','')).stem or p.stem
  out=p.with_name(epos+' deconvoluted range file.json')
  payload=json_safe({'format':'aptpy-deconvoluted-range-analysis','version':1,'source_project':str(p),'source_epos':project.get('epos_file'),'range_count':len(result['range_fit']),'shared_range_count':int((result['range_fit']['checked_species']>1).sum()),'warnings':result['warnings'],'ion_estimates':ions.to_dict('records'),'element_composition':atoms.to_dict('records'),'range_fit':result['range_fit'].to_dict('records'),'shares':result['shares'].to_dict('records'),'group_diagnostics':result['group_diagnostics'].to_dict('records')})
  payload['shared_peak_details']=peaks
  payload['analysis_settings']={'isotope_source':'apav','bootstrap_repeats':200,'background_counts':None}
  fd,tmp=tempfile.mkstemp(prefix='.'+out.name,dir=out.parent);os.close(fd);Path(tmp).write_text(json.dumps(payload,indent=2,allow_nan=False));os.replace(tmp,out)
  return json_safe({'output_path':str(out),'range_count':len(result['range_fit']),'species_count':len(ions),'shared_count':int((result['range_fit']['checked_species']>1).sum()),'composition':atoms.to_dict('records'),'ions':ions[['ion','formula','charge','ion_count','status']].to_dict('records'),'warnings':result['warnings'],'shared_peaks':peaks})
def main():
 app=App();token=secrets.token_urlsafe(24)
 class H(BaseHTTPRequestHandler):
  def log_message(self,*a):pass
  def do_GET(self):
   raw=(ROOT/'index.html').read_text().replace('__TOKEN__',token).encode();self.send_response(200);self.send_header('Content-Type','text/html');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
  def do_POST(self):
   if self.headers.get('X-Editor-Token')!=token:self.send_error(403);return
   try:
    b=json.loads(self.rfile.read(int(self.headers.get('Content-Length',0))) or '{}')
    if self.path=='/open':
     r=subprocess.run(['osascript','-e','POSIX path of (choose file with prompt "Open APT project JSON")'],capture_output=True,text=True);d={'cancelled':True} if r.returncode else {'path':r.stdout.strip()}
    elif self.path=='/analyse':d=app.run(b['path'])
    else:raise ValueError('Unknown action')
    raw=json.dumps(d,allow_nan=False).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
   except Exception as e:
    raw=json.dumps({'error':str(e)}).encode();self.send_response(400);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
 s=ThreadingHTTPServer(('127.0.0.1',0),H);url=f'http://127.0.0.1:{s.server_port}/';print(url,flush=True)
 if '--no-browser' not in sys.argv:webbrowser.open(url)
 s.serve_forever()
if __name__=='__main__':main()
