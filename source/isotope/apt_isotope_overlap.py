"""Isotope-constrained peak-area mixture fitting; APAV + scipy. No project mutation.

This is a custom global spectrum model, not an APAV built-in or an event identity solver.
Fixed isotope fingerprints, equal isotope-window capture efficiency, specified candidate
identities and optional fixed background are assumptions. Shares are conditional on them.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from scipy.optimize import minimize, nnls
from scipy.special import xlogy
from scipy.stats import chi2


def formula_text(comp):
    return ''.join(e + (str(n) if n != 1 else '') for e, n in comp.items())


def identity(ion):
    return (tuple(sorted(ion['formula'].items())), int(ion['charge']))


def checked_ions(r):
    if isinstance(r.get('ion_candidates'), list):
        return [i for i in r['ion_candidates'] if i.get('selected') is True
                and r['lower_mz'] <= i.get('exact_mz', -1) < r['upper_mz']]
    return [i for i in r.get('ions', []) if i.get('selected') is not False]


def build_model(project, isotope_source='apav'):
    """A[r,j] is species j's natural isotope probability inside range r.

    Unchecked species are excluded per range. Reported conflicts identify theoretical
    isotope peaks falling in a window where that globally fitted species was unchecked.
    'project' uses the saved unthresholded natural-abundance isotope tables instead.
    """
    ranges = sorted(project['range_editor']['ranges'], key=lambda r: r['lower_mz'])
    if not ranges:
        raise ValueError('No ranges in this project.')
    for k, r in enumerate(ranges):
        if not 0 <= r['lower_mz'] < r['upper_mz']:
            raise ValueError('Invalid range boundaries.')
        if k and r['lower_mz'] < ranges[k-1]['upper_mz']:
            raise ValueError('Ranges overlap. Make the integration windows disjoint.')
    species = {}
    for r in ranges:
        for ion in checked_ions(r):
            species.setdefault(identity(ion), dict(ion))
    species = list(species.values())
    if not species:
        raise ValueError('No checked candidates in the ranges.')
    reference = {identity(i): i for i in project.get('selected_ions', [])}
    patterns = []
    for ion in species:
        if isotope_source == 'apav':
            import apav as ap
            series = ap.IsotopeSeries(formula_text(ion['formula']), int(ion['charge']), threshold=0)
            masses, probs = np.array(series.masses), np.array(series.abundances)
        elif isotope_source == 'project':
            saved = reference.get(identity(ion), {}).get('isotopes', [])
            if not saved:
                raise ValueError('No saved isotope pattern for ' + ion['ion_key'])
            masses = np.array([i['exact_mz'] for i in saved])
            probs = np.array([i['natural_isotope_share_percent']/100 for i in saved])
        else:
            raise ValueError('isotope_source must be apav or project.')
        if not np.isclose(probs.sum(), 1, atol=1e-5):
            raise ValueError('Incomplete isotope pattern for ' + ion['ion_key'] + '; use APAV threshold=0.')
        patterns.append((masses, probs))
    A = np.zeros((len(ranges), len(species)))
    conflicts = []
    for k, r in enumerate(ranges):
        allowed = {identity(i) for i in checked_ions(r)}
        for j, (ion, (mass, probability)) in enumerate(zip(species, patterns)):
            p = probability[(mass >= r['lower_mz']) & (mass < r['upper_mz'])].sum()
            if identity(ion) in allowed:
                A[k, j] = p
            elif p > 1e-5:
                conflicts.append({'range_number': k+1, 'ion': ion['ion_label'], 'isotope_probability': float(p)})
    return {'ranges': ranges, 'species': species, 'A': A,
            'excluded_candidate_conflicts': conflicts, 'isotope_source': isotope_source}


def count_ranges(model, project=None, epos_path=None, mass=None, chunk_size=1_000_000):
    """Exact counts from an EPOS mass field / APAV Roi.mass; cached bins are a preview.

    EPOS is the conventional 11 x 4-byte big-endian record; the fourth float is m/q.
    A chunked memory map avoids loading the complete reconstruction into memory.
    Half-open [lower, upper) windows match APAV's counting convention.
    """
    ranges = model['ranges']
    lo = np.array([r['lower_mz'] for r in ranges]); hi = np.array([r['upper_mz'] for r in ranges])
    result = np.zeros(len(ranges), dtype=float)
    def accumulate(values):
        values = np.asarray(values)
        idx = np.searchsorted(lo, values, side='right') - 1
        valid = (idx >= 0) & np.isfinite(values)
        ids = idx[valid]; vals = values[valid]
        result[:] += np.bincount(ids[vals < hi[ids]], minlength=len(ranges))
    if epos_path is not None:
        path = Path(epos_path).expanduser()
        if path.stat().st_size % 44:
            raise ValueError('EPOS file size is not a multiple of 44 bytes.')
        records = np.memmap(path, dtype='>f4', mode='r').reshape(-1, 11)
        for start in range(0, len(records), chunk_size):
            accumulate(records[start:start+chunk_size, 3])
        return result, 'exact EPOS counts'
    if mass is not None:
        for start in range(0, len(mass), chunk_size):
            accumulate(mass[start:start+chunk_size])
        return result, 'exact supplied event-mass counts'
    if project is None or not project.get('spectrum_cache'):
        raise ValueError('Provide EPOS, event masses, or a cached project spectrum.')
    cache = project['spectrum_cache']; x = np.asarray(cache['mass']); y = np.asarray(cache['counts'])
    if x.shape != y.shape or not np.all(np.isfinite(y)) or np.any(y < 0):
        raise ValueError('Invalid cached histogram.')
    for k in range(len(ranges)):
        result[k] = y[(x >= lo[k]) & (x < hi[k])].sum()
    return result, 'cached-bin approximation (boundary bins can differ from exact counts)'


def poisson_fit(A, y, background=None):
    """Fit nonnegative counts with fixed additive background. A must be identifiable."""
    A = np.asarray(A, float); y = np.asarray(y, float)
    b = np.zeros_like(y) if background is None else np.asarray(background, float)
    if A.ndim != 2 or y.shape != (len(A),) or b.shape != y.shape:
        raise ValueError('Matrix/count/background shape mismatch.')
    if np.any(A < 0) or np.any(y < 0) or np.any(b < 0) or not all(np.isfinite(z).all() for z in (A,y,b)):
        raise ValueError('Inputs must be finite and nonnegative.')
    coverage = A.sum(axis=0)
    if np.any(coverage <= 0):
        raise ValueError('A species has no isotope inside its selected ranges.')
    P = A / coverage
    if np.linalg.matrix_rank(P) < P.shape[1]:
        raise ValueError('Isotope patterns are rank deficient; a unique split cannot be determined.')
    scale = max(float(y.sum()), 1.)
    yn, bn = y/scale, b/scale
    weights = np.sqrt(np.maximum(y, 1))
    guess = nnls(P/weights[:,None], np.maximum(y-b,0)/weights)[0]/scale
    def objective(q):
        mu = np.maximum(P @ q + bn, 1e-300)
        return float(np.sum(mu - xlogy(yn,mu))), P.T @ (1 - yn/mu)
    if y.sum() == 0:
        return np.zeros(A.shape[1]), b.copy()
    fit = minimize(objective, np.maximum(guess,1e-12), jac=True, method='L-BFGS-B',
                   bounds=[(0,None)]*len(coverage),
                   options={'ftol':1e-13,'gtol':1e-10,'maxiter':5000,'maxls':60})
    if not fit.success:
        raise RuntimeError('Poisson optimization failed: ' + fit.message)
    theta = fit.x*scale/coverage
    return theta, A@theta+b


def components(A):
    """Independent connected groups of overlapping species and their windows."""
    remaining = set(range(A.shape[1]))
    while remaining:
        cols = {min(remaining)}; rows = set()
        while True:
            new_rows = set(np.flatnonzero((A[:,list(cols)] > 0).any(axis=1)))
            new_cols = cols | (set(np.flatnonzero((A[list(new_rows),:] > 0).any(axis=0))) if new_rows else set())
            if new_cols == cols:
                rows = new_rows; break
            cols = new_cols
        remaining -= cols
        yield np.array(sorted(rows),int), np.array(sorted(cols),int)


def analyse(project, isotope_source='apav', epos_path=None, mass=None, counts=None,
            background_counts=None, bootstrap=100, seed=865):
    """Return conditional peak shares plus diagnostics. No input files are changed.

    Bootstrap intervals include Poisson counting error at fixed background, candidate
    set and natural isotope ratios; they do NOT include systematic uncertainty.
    Poor-fit groups are explicitly marked. Rank-deficient groups get no fitted shares.
    """
    model = build_model(project, isotope_source)
    A = model['A']
    if counts is None:
        y, count_source = count_ranges(model, project, epos_path, mass)
    else:
        y = np.asarray(counts,float); count_source='supplied integrated counts'
    b = np.zeros_like(y) if background_counts is None else np.asarray(background_counts,float)
    if y.shape != (len(A),) or b.shape != y.shape or not np.isfinite(y).all() or not np.isfinite(b).all() or np.any(y<0) or np.any(b<0):
        raise ValueError('Invalid integrated counts/background.')
    rng = np.random.default_rng(seed)
    estimates=[];groups=[];fitted=np.full(len(y),np.nan);species_rows=[]
    for group, (rr, cc) in enumerate(components(A), 1):
        M=A[np.ix_(rr,cc)]; obs=y[rr]; bg=b[rr]
        coverage=M.sum(axis=0)
        rank=np.linalg.matrix_rank(M/np.maximum(coverage,1e-300)) if len(rr) else 0
        names=[model['species'][j]['ion_label'] for j in cc]
        base={'group':group,'ions':' / '.join(names),'windows':len(rr),'species':len(cc),'rank':int(rank)}
        if rank < len(cc) or np.any(coverage<=0):
            groups.append({**base,'status':'not_identifiable','message':'No unique split from these windows/isotope patterns.'})
            for k in rr:
                for j in cc:
                    if A[k,j]>0:
                        estimates.append({'range_number':int(k+1),'ion':model['species'][j]['ion_label'],'status':'not_identifiable','signal_share_percent':np.nan,'allocated_detected_ions':np.nan})
            continue
        theta,mu=poisson_fit(M,obs,bg);fitted[rr]=mu
        signal=M*theta[None,:];total=signal.sum(axis=1)
        fraction=np.divide(signal,total[:,None],out=np.full_like(signal,np.nan),where=total[:,None]>0)
        responsibilities=np.divide(signal,mu[:,None],out=np.zeros_like(signal),where=mu[:,None]>0)
        allocated=obs[:,None]*responsibilities
        deviance=float(2*np.sum(xlogy(obs,np.divide(obs,np.maximum(mu,1e-300)))-(obs-mu)))
        dof=len(rr)-len(cc);pvalue=float(chi2.sf(max(deviance,0),dof)) if dof>0 else np.nan
        status='no_redundant_check' if dof<=0 else ('model_misfit' if pvalue<.01 else 'conditional_estimate')
        ratio=np.linalg.svd(M/coverage,compute_uv=False)
        condition=float(ratio[0]/ratio[-1])
        trials=[];failures=0
        for _ in range(int(bootstrap)):
            try:
                t,_=poisson_fit(M,rng.poisson(mu),bg)
                z=M*t[None,:];den=z.sum(axis=1)
                trials.append(np.divide(z,den[:,None],out=np.full_like(z,np.nan),where=den[:,None]>0))
            except (RuntimeError,ValueError):failures+=1
        intervals=np.nanpercentile(np.array(trials),[2.5,97.5],axis=0)*100 if trials else None
        groups.append({**base,'status':status,'poisson_deviance':deviance,'degrees_of_freedom':dof,
                       'approx_fit_pvalue':pvalue,'pattern_condition_number':condition,'bootstrap_failures':failures})
        for col,j in enumerate(cc):
            ion=model['species'][j]
            species_rows.append({'group':group,'ion':ion['ion_label'],'formula':formula_text(ion['formula']),
                                 'charge':ion['charge'],'status':status,'captured_isotope_probability':coverage[col],
                                 'fitted_full_pattern_ions':theta[col],'allocated_ions_in_windows':allocated[:,col].sum()})
            for row,k in enumerate(rr):
                if M[row,col]<=0:continue
                estimates.append({'range_number':int(k+1),'ion':ion['ion_label'],'formula':formula_text(ion['formula']),
                                  'charge':ion['charge'],'status':status,'signal_share_percent':100*fraction[row,col],
                                  'share_low95_percent':intervals[0,row,col] if intervals is not None else np.nan,
                                  'share_high95_percent':intervals[1,row,col] if intervals is not None else np.nan,
                                  'fraction_of_all_peak_counts_percent':100*responsibilities[row,col],
                                  'allocated_detected_ions':allocated[row,col],
                                  'fitted_signal_ions':signal[row,col]})
    range_rows=[]
    for k,r in enumerate(model['ranges']):
        range_rows.append({'range_number':k+1,'range_id':r.get('id'),'lower_mz':r['lower_mz'],'upper_mz':r['upper_mz'],
                           'observed_ions':y[k],'fixed_background_ions':b[k],'fitted_total_ions':fitted[k],
                           'pearson_residual':(y[k]-fitted[k])/np.sqrt(max(fitted[k],1)) if np.isfinite(fitted[k]) else np.nan,
                           'checked_species':int((A[k]>0).sum())})
    warnings=['These are conditional global peak-area estimates, not identities of individual detected ions.',
              'Assumes natural isotope abundances, complete candidate identities, and comparable capture of each isotope peak by its integration window.',
              'Bootstrap intervals cover counting variation only, at fixed model and fixed background.']
    if background_counts is None:warnings.append('No background correction supplied: raw-count estimates are preliminary.')
    if count_source.startswith('cached'):warnings.append('Cached bin integration is approximate. Use EPOS or data.mass for exact boundaries.')
    if model['excluded_candidate_conflicts']:warnings.append('Some isotope lines fall in windows where that fitted species was unchecked: review excluded_candidate_conflicts.')
    if any(g['status']=='model_misfit' for g in groups):warnings.append('Some isotope groups fail the Poisson fit check: their shares are model-inconsistent and require review, not reporting as validated composition.')
    if any(g['status']=='no_redundant_check' for g in groups):warnings.append('Some groups have no redundant isotope windows: their fit cannot independently check the assumed identities or natural isotope ratios.')
    if any(g['status']=='not_identifiable' for g in groups):warnings.append('Some groups are not identifiable: their shares have intentionally been left blank.')
    return {'shares':pd.DataFrame(estimates),'range_fit':pd.DataFrame(range_rows),
            'species_fit':pd.DataFrame(species_rows),'group_diagnostics':pd.DataFrame(groups),
            'warnings':warnings,'count_source':count_source,'model':model,
            'background_supplied':background_counts is not None}


def save_tables(result, output_folder):
    """Write a new analysis folder, preserving the original project and range files."""
    folder=Path(output_folder).expanduser()
    folder.mkdir(parents=True,exist_ok=False)
    for name in ('shares','range_fit','species_fit','group_diagnostics'):
        result[name].to_csv(folder/(name+'.csv'),index=False)
    pd.DataFrame(result['model']['excluded_candidate_conflicts']).to_csv(folder/'excluded_candidate_conflicts.csv',index=False)
    (folder/'analysis_notes.txt').write_text(result['count_source']+'\n\n'+'\n'.join(result['warnings'])+'\n',encoding='utf-8')
    return folder
