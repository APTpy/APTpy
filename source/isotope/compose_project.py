"""Run isotope-overlap analysis and report ion, atom, at.% and wt.% totals.

The input project JSON is never modified.  Results are written to a new folder.
"""
from pathlib import Path
import argparse, json
import pandas as pd
from apt_isotope_overlap import build_model, analyse, save_tables

try:
    import periodictable as pt
except ImportError:
    pt = None

FALLBACK_MASS = {'H': 1.008, 'C': 12.011, 'O': 15.999, 'Al': 26.9815385,
                 'Si': 28.085, 'Mn': 54.938044, 'Fe': 55.845, 'Cr': 51.9961,
                 'Ni': 58.6934, 'Mo': 95.95, 'N': 14.007, 'Ti': 47.867}

def atomic_mass(symbol):
    if pt is not None:
        return float(getattr(pt, symbol).mass)
    if symbol not in FALLBACK_MASS:
        raise KeyError(f'Add an atomic mass for {symbol!r} or install periodictable.')
    return FALLBACK_MASS[symbol]

def composition_tables(result):
    """Return ion totals, elemental atom totals, atomic percent and weight percent."""
    ions = result['species_fit'].copy()
    ions['ion_count'] = ions['fitted_full_pattern_ions'].clip(lower=0)
    atom_rows = []
    for _, row in ions.iterrows():
        ion = result['model']['species'][int(row.name)] if int(row.name) < len(result['model']['species']) else None
        # Match by label/charge because DataFrame indexes are not guaranteed after filtering.
        if ion is None or ion.get('ion_label') != row['ion']:
            ion = next(x for x in result['model']['species']
                       if x['ion_label'] == row['ion'] and int(x['charge']) == int(row['charge']))
        for element, number in ion['formula'].items():
            atom_rows.append({'element': element, 'atom_count': row['ion_count'] * number})
    atoms = pd.DataFrame(atom_rows).groupby('element', as_index=False)['atom_count'].sum()
    atoms['at_percent'] = 100 * atoms['atom_count'] / atoms['atom_count'].sum()
    atoms['mass_contribution'] = atoms.apply(lambda r: r['atom_count'] * atomic_mass(r['element']), axis=1)
    atoms['wt_percent'] = 100 * atoms['mass_contribution'] / atoms['mass_contribution'].sum()
    return ions, atoms

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('project_json', type=Path)
    ap.add_argument('-o', '--output', type=Path, default=None)
    ap.add_argument('--isotope-source', choices=('apav', 'project'), default='apav')
    ap.add_argument('--bootstrap', type=int, default=200)
    args = ap.parse_args()
    project = json.loads(args.project_json.read_text(encoding='utf-8'))
    result = analyse(project, isotope_source=args.isotope_source, bootstrap=args.bootstrap)
    out = args.output or args.project_json.with_name(args.project_json.stem + '_isotope-analysis')
    out.mkdir(parents=True, exist_ok=False)
    for name in ('shares', 'range_fit', 'species_fit', 'group_diagnostics'):
        result[name].to_csv(out / (name + '.csv'), index=False)
    ions, atoms = composition_tables(result)
    ions.to_csv(out / 'ion_totals.csv', index=False)
    atoms.to_csv(out / 'element_composition.csv', index=False)
    (out / 'analysis_notes.txt').write_text('\n'.join(result['warnings']) + '\n', encoding='utf-8')
    print(f'Wrote analysis to {out}')
    print(atoms[['element', 'atom_count', 'at_percent', 'wt_percent']].to_string(index=False))

if __name__ == '__main__':
    main()
