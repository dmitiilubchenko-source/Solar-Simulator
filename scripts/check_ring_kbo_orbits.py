"""Assess all freely integrated KBOs against later SB441, keeping worse results."""
import hashlib
import json
from pathlib import Path
import numpy as np

from scripts.assess_kuiper_ring import grid,checked_cache
from scripts.assess_kuiper import source_residual
from scripts.assess_pluto import reference
from scripts.assess_solar_j2 import PLANET_REFERENCE_SHA256
from scripts.fetch_kuiper_data import inputs,year_blocks,decode_year,YEAR_MANIFEST_SHA,PACKED_SHA
from solar_simulator.kuiper_ring import solar_system_ring
from solar_simulator.perturbers import solar_system_kuiper


def main():
    _,_,_,times=grid();arrays,metadata=checked_cache('ring-production',times)
    rows,manifest,segments,_,=inputs()
    records=decode_year(manifest,year_blocks(manifest),segments,{r['id'] for r in rows})
    planets=reference('docs/solar-system-reference.json',PLANET_REFERENCE_SHA256)
    results={}
    for name,array in arrays.items():
        settings=metadata['runs'][name]
        bodies,origin=solar_system_kuiper() if settings['points'] is None else solar_system_ring(settings['points'],settings['phase_index'])
        values=source_residual(array,bodies,times,planets,rows,records)
        if len(values)!=30 or any(not np.isfinite(v['maximum_position_metres']) for v in values.values()):
            raise ValueError('Incomplete/nonfinite freely propagated KBO residuals')
        results[name]=dict(dataset_sha256=origin.dataset_sha256,bodies=values)
    code=('scripts/check_ring_kbo_orbits.py','scripts/assess_kuiper.py','scripts/fetch_kuiper_data.py',
        'scripts/assess_kuiper_ring.py')
    report=dict(schema=1,body_count=30,source_samples=13,variants=results,
        source_manifest_sha256=YEAR_MANIFEST_SHA,packed_source_sha256=PACKED_SHA,
        production_archive_sha256=metadata['archive_sha256'],audit_checks_passed=True,
        code_sha256={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in code},
        limitations=['Assessment only after free propagation; SB441 does not drive the integrated target trajectories.',
            'SSB comparison uses the reference Sun plus original heliocentric SPK state.',
            'Includes conditional reference Sun error; not independent physical truth.',
            'Large SB441 residual can reflect a different dynamical model; cause is not identified here.',
            'audit_checks_passed validates data and provenance, not accuracy of all KBO orbits.'])
    Path('docs/kuiper-ring-kbo-validation.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    for name,value in results.items():
        worst=max((b['maximum_position_metres'],body) for body,b in value['bodies'].items())
        print(name,'maximum KBO source residual',worst,flush=True)


if __name__=='__main__':main()
