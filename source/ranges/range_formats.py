"""ORNL RNG / IVAS RRNG writers with explicit shared-assignment semantics."""
import copy
import colorsys
import hashlib
import json
import math
import re
from pathlib import Path


def validate_ranges(ranges):
    if not isinstance(ranges, list):
        raise ValueError('Ranges must be a list.')
    for i, r in enumerate(ranges, 1):
        lo, hi = r.get('lower_mz'), r.get('upper_mz')
        if not (type(lo) in (float, int) and type(hi) in (float, int)
                and math.isfinite(lo) and math.isfinite(hi) and 0 <= lo < hi):
            raise ValueError(f'Invalid boundaries in range {i}.')
        if not isinstance(r.get('ions'), list):
            raise ValueError(f'Invalid assignments in range {i}.')


def formula(ion):
    value = ion.get('formula')
    if not isinstance(value, dict) or not value:
        raise ValueError('An assigned ion is missing its chemical formula.')
    for element, count in value.items():
        if not re.fullmatch(r'[A-Z][a-z]?', element) or type(count) is not int or count < 1:
            raise ValueError('An assigned ion has an invalid chemical formula.')
    return value


def species_name(ion):
    composition = formula(ion)
    charge = ion.get('charge')
    if type(charge) is not int or charge < 1:
        raise ValueError('An assigned ion is missing its positive charge state.')
    return ''.join(e + (str(n) if n != 1 else '') for e, n in composition.items()) + 'q' + str(charge)


def colour(name):
    hue = int(hashlib.sha256(name.encode()).hexdigest()[:8], 16) / 0xffffffff
    return tuple(round(x * 255) for x in colorsys.hsv_to_rgb(hue, .62, .82))


def selected_ions(r):
    """Use explicit saved checkbox states; legacy projects retain their selected-ion list."""
    choices = r.get('ion_candidates')
    if isinstance(choices, list):
        return [{k: v for k, v in ion.items() if k not in ('selected', 'in_range')} for ion in choices
                if ion.get('selected') is True and r['lower_mz'] <= ion.get('exact_mz', -1) <= r['upper_mz']]
    return [ion for ion in r.get('ions', []) if ion.get('selected') is not False]


def build_export(ranges, file_format='rrng', mode='ions', volume=0.0):
    """Resolved formulas are elemental stoichiometry; alternatives are named unknowns."""
    if file_format not in ('rng', 'rrng'):
        raise ValueError('Choose .rng or .rrng.')
    if type(volume) not in (int, float) or not math.isfinite(volume) or volume < 0:
        raise ValueError('Volume must be finite and nonnegative.')
    validate_ranges(ranges)
    if not ranges:
        raise ValueError('Create at least one range before exporting.')
    ordered = sorted(copy.deepcopy(ranges), key=lambda r: r['lower_mz'])
    rows, elements, unresolved = [], {}, []
    for i, r in enumerate(ordered, 1):
        if i > 1 and r['lower_mz'] < ordered[i - 2]['upper_mz']:
            raise ValueError(f'Ranges {i-1} and {i} overlap. Adjust their boundaries before exporting.')
        r['ions'] = selected_ions(r)
        compositions = {json.dumps(formula(ion), sort_keys=True) for ion in r['ions']}
        counts = dict(formula(r['ions'][0])) if len(compositions) == 1 else {}
        unknown = None
        if not counts:
            reason = 'shared' if r['ions'] else 'unassigned'
            labels = sorted({species_name(ion) for ion in r['ions']})
            unknown = ('Shared_' + '_OR_'.join(labels) if labels else 'Unassigned') + f'_R{i}'
            unresolved.append({'range_number': i, 'range_id': r.get('id'), 'reason': reason,
                               'lower_mz': r['lower_mz'], 'upper_mz': r['upper_mz'],
                               'selected_ions': r['ions']})
            if file_format == 'rng':
                raise ValueError(f'Range {i} is {reason}. Use .rrng to preserve its boundaries as a named range, or resolve its composition before .rng export.')
        for name in counts:
            elements.setdefault(name, colour(name))
        lo, hi = (f"{r[k]:.12f}" for k in ('lower_mz', 'upper_mz'))
        if float(lo) >= float(hi):
            raise ValueError(f'Range {i} is too narrow to export at 12 decimal places.')
        rows.append((lo, hi, counts, unknown))
    names = list(elements)
    if file_format == 'rrng':
        lines = ['[Ions]', f'Number={len(names)}']
        lines += [f'Ion{i}={name}' for i, name in enumerate(names, 1)]
        lines += ['[Ranges]', f'Number={len(rows)}']
        for i, (lo, hi, counts, unknown) in enumerate(rows, 1):
            rgb = colour(unknown or json.dumps(counts, sort_keys=True))
            assignment = 'Name:' + unknown if unknown else ' '.join(f'{name}:{n}' for name, n in counts.items())
            lines.append(f'Range{i}={lo} {hi} Vol:{volume:.8f} ' + assignment + ' Color:' + ''.join(f'{x:02X}' for x in rgb))
    else:
        lines = [f'{len(names)} {len(rows)}']
        for name, rgb in elements.items():
            lines += [name, name + ' ' + ' '.join(f'{x/255:.6f}' for x in rgb)]
        lines += ['------------- ' + ' '.join(names)]
        lines += [f'. {lo} {hi} ' + ' '.join(str(counts.get(name, 0)) for name in names) for lo, hi, counts, _ in rows]
    manifest = {
        'format': 'aptpy-range-export-assignments', 'version': 2,
        'range_file_format': file_format, 'assignment_style': 'elemental-with-named-unresolved',
        'units': 'Da/e', 'volume_nm3': volume if file_format == 'rrng' else None,
        'interpretation': 'Resolved ranges use elemental stoichiometry. Shared alternatives and unassigned ranges use Name entries. APAV skips Name entries; no deconvolution is implied.',
        'species': {species_name(ion): {'label': ion.get('ion_label'), 'formula': ion['formula'], 'charge': ion['charge']} for r in ordered for ion in r['ions']},
        'resolved_range_count': len(rows) - len(unresolved),
        'unresolved_range_count': len(unresolved), 'unresolved_ranges': unresolved,
        'ranges': ordered,
    }
    return '\n'.join(lines) + '\n', manifest


def write_export(project_path, ranges, file_format, mode='ions', volume=0.0, folder=None):
    text, manifest = build_export(ranges, file_format, mode, volume)
    project_path = Path(project_path)
    directory = Path(folder).expanduser().resolve() if folder else project_path.parent
    if not directory.is_dir():
        raise ValueError('Choose an existing output folder.')
    stem = project_path.name.removesuffix('.apt-project.json').removesuffix('.json') + '_ranges'
    for index in range(10000):
        suffix = '' if index == 0 else f'_{index+1}'
        target = directory / f'{stem}{suffix}.{file_format}'
        try:
            f = target.open('x', encoding='ascii', newline='\n')
        except FileExistsError:
            continue
        try:
            with f:
                f.write(text)
            manifest['range_file'] = target.name
        except Exception:
            target.unlink(missing_ok=True)
            raise
        return {'path': str(target), 'manifest': manifest, 'range_count': len(ranges), 'resolved_range_count': manifest['resolved_range_count'], 'unresolved_range_count': manifest['unresolved_range_count']}
    raise ValueError('No unused export filename is available.')
