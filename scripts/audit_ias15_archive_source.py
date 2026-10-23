"""Pinned upstream source inventory, without importing or executing REBOUND."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
import tarfile
from time import perf_counter

SDIST_SHA = 'cefb2bce433a134e0f6fa0cb68df01079b0a5c160fadd2a2c85b06f286735a5f'
FILES = ('src/integrator_ias15.h', 'src/integrator_ias15.c', 'src/binarydata.c',
         'src/binarydata.h', 'src/simulation.c', 'src/simulationarchive.c',
         'src/rebound.h', 'rebound/simulation.py', 'rebound/simulationarchive.py')
SCALARS = ('epsilon', 'min_dt', 'adaptive_mode', 'iterations_max_exceeded')
VECTORS = ('at', 'x0', 'v0', 'a0', 'csx', 'csv', 'csa0')
POLYNOMIALS = ('g', 'b', 'csb', 'e', 'br', 'er')


def descriptors(text, structure):
    pattern = r'(REB_[A-Z0-9_]+),\s*"([^"]+)",\s*offsetof\(struct '+structure+r',\s*([\w.]+)\)([^}]*?)}'
    rows = {}
    for match in re.finditer(pattern, text):
        dtype, name, member, tail = match.groups()
        if name in rows:raise ValueError('Duplicate binary field: '+name)
        rows[name] = dict(dtype=dtype, member=member, line=text[:match.start()].count('\n')+1,
                          tail=tail.strip())
    if not rows:raise ValueError('No descriptor fields')
    return rows


def ias15_fields(header, implementation):
    body = header.split('struct reb_integrator_ias15_state {', 1)[1].split('\n};', 1)[0]
    declared = re.findall(r'^\s*(?:double\*\s+REB_RESTRICT|double|uint64_t|size_t)\s+(\w+)\s*;', body, re.M)
    declared += re.findall(r'}\s*(\w+)\s*;', body)
    expected = set((*SCALARS, *VECTORS, *POLYNOMIALS, 'N_allocated'))
    if len(declared) != len(set(declared)) or set(declared) != expected:
        raise ValueError('Unexpected IAS15 structure fields')
    rows = descriptors(implementation, 'reb_integrator_ias15_state')
    if set(rows) != expected-{'N_allocated'}:
        raise ValueError('Missing or extra IAS15 descriptor fields')
    types = dict(epsilon='REB_DOUBLE', min_dt='REB_DOUBLE', adaptive_mode='REB_UINT',
                 iterations_max_exceeded='REB_UINT64')
    for name, row in rows.items():
        if row['member'] != name:raise ValueError('IAS15 descriptor aliases another member')
        if name in types:
            if row['dtype'] != types[name]:raise ValueError('Wrong IAS15 scalar type')
            row['elements_per_allocated_coordinate'] = None
        else:
            count = 1 if name in VECTORS else 7
            if (row['dtype'] != 'REB_POINTER'
                    or 'offsetof(struct reb_integrator_ias15_state, N_allocated)' not in row['tail']
                    or not re.search(r',\s*'+('' if count == 1 else r'7\*')+r'sizeof\(double\),', row['tail'])):
                raise ValueError('Wrong IAS15 pointer length or type')
            row['elements_per_allocated_coordinate'] = count
        del row['tail']
    return rows


def warning_inventory(c_header, python_source):
    declared = {name:int(number) for name,number in re.findall(r'(REB_BINARYDATA_\w+)\s*=\s*(\d+)', c_header)
                if name.startswith(('REB_BINARYDATA_WARNING_', 'REB_BINARYDATA_ERROR_')) and int(number)}
    tree = ast.parse(python_source)
    node = next(node for node in tree.body if isinstance(node, ast.Assign)
                and any(isinstance(target, ast.Name) and target.id == 'BINARY_WARNINGS' for target in node.targets))
    python_bits = [item[1] for item in ast.literal_eval(node.value)]
    if len(python_bits) != len(set(python_bits)):raise ValueError('Duplicate Python warning bit')
    return dict(c_declared=declared, python_mapped=python_bits,
                c_declared_not_python_mapped={k:v for k,v in declared.items() if v not in python_bits})


def read_sources(path):
    if hashlib.sha256(Path(path).read_bytes()).hexdigest() != SDIST_SHA:
        raise ValueError('Pinned REBOUND sdist SHA mismatch')
    result = {}
    with tarfile.open(path, 'r:gz') as archive:
        for name in FILES:
            full = 'rebound-5.2.2/'+name
            members = [m for m in archive.getmembers() if m.name == full]
            if len(members) != 1 or not members[0].isfile():
                raise ValueError('Missing, duplicate or non-regular upstream source: '+name)
            result[name] = archive.extractfile(members[0]).read()
    return result


def audit(path):
    start = perf_counter()
    raw = read_sources(path)
    text = {name:data.decode('utf-8') for name,data in raw.items()}
    fields = ias15_fields(text[FILES[0]], text[FILES[1]])
    global_rows = descriptors(text['src/binarydata.c'], 'reb_simulation')
    required = ('t', 'G', 'dt', 'dt_last_done', 'steps_done', 'N', 'particles', 'gravity',
                'softening', 'force_is_velocity_dependent', 'exact_finish_time', 'integrator.name')
    if not set(required) <= set(global_rows):raise ValueError('Required global fields missing')
    evidence = {
        'writer_integrator_fields': ('src/binarydata.c', 'output_fields_from_list(bufp, current_pos, &allocatedsize, r->integrator.callbacks.field_descriptor_list'),
        'writer_array_bytes': ('src/binarydata.c', 'field.size_data = pointer_N * fd.element_size;'),
        'reader_derives_allocation': ('src/binarydata.c', '*pointer_N = (size_t)field.size_data/fd.element_size;'),
        'reader_resets_particle_ap': ('src/binarydata.c', 'r->particles[l].ap = NULL;'),
        'reader_ignores_githash': ('src/binarydata.c', 'following compares version, but ignores githash'),
        'writer_pointer_warning': ('src/binarydata.c', 'int functionpointersused = 0;'),
        'file_first_full_snapshot': ('src/simulationarchive.c', 'reb_binarydata_simulation_to_stream(r, &bufp,&sizep);'),
        'file_existing_appends': ('src/simulationarchive.c', 'File exists, append snapshot.'),
        'python_stream_export': ('rebound/simulation.py', 'def __reduce__(self):'),
        'python_stream_constructor': ('rebound/simulation.py', 'if isinstance(args[0], bytes):'),
        'python_exact_load_can_integrate': ('rebound/simulationarchive.py', 'sim.integrate(t,exact_finish_time=1)'),
        'packet_api_resets_dt_last': ('src/simulation.c', 'r->dt_last_done = 0.;'),
    }
    spans = {}
    for label,(name,needle) in evidence.items():
        if needle not in text[name]:raise ValueError('Missing audited source evidence: '+label)
        spans[label] = dict(file=name, line=text[name][:text[name].index(needle)].count('\n')+1)
    warnings = warning_inventory(text['src/binarydata.h'], text['rebound/simulation.py'])
    callback_flag = text['src/binarydata.c'].split('int functionpointersused = 0;', 1)[1].split('functionpointersused = 1;', 1)[0]
    flagged_callbacks = re.findall(r'r->(\w+)', callback_flag)
    if len(flagged_callbacks) != len(set(flagged_callbacks)) or 'additional_forces' not in flagged_callbacks:
        raise ValueError('Unexpected callback warning flag inventory')
    return dict(schema=1,stage=362,rebound_version='5.2.2',sdist_sha256=SDIST_SHA,
        upstream_files={n:dict(sha256=hashlib.sha256(b).hexdigest(),lines=len(b.splitlines()),
            url='https://github.com/hannorein/rebound/blob/5.2.2/'+n) for n,b in raw.items()},
        ias15_declared_fields=18,ias15_written_fields=fields,derived_fields=['N_allocated'],
        global_written_fields={n:{k:v for k,v in global_rows[n].items() if k!='tail'} for n in required},
        warning_inventory=warnings,callback_warning_flag_fields=flagged_callbacks,evidence=spans,
        controller_array_doubles_per_allocated_coordinate=sum(r['elements_per_allocated_coordinate'] or 0 for r in fields.values()),
        decision='feasible-to-test-same-build-trusted-snapshot; numerical continuation unqualified',
        numerical_experiment_executed=False,runtime_modified=False,production_eligible=False,
        elapsed_seconds=perf_counter()-start)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():raise FileExistsError('Preserve the previous audit')
    result = audit(args.source)
    with args.output.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps(dict(output=str(args.output),written_fields=len(result['ias15_written_fields']),
                          derived=result['derived_fields'],decision=result['decision'])))


if __name__ == '__main__':main()
