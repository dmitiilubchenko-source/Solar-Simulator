"""Explicit research command; GUI/Experiment velocity schemas are not accepted."""
import argparse
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT)); sys.path.insert(0,str(ROOT/'src'))
from scripts import lunar_research as research
from scripts.canonical_initial import SIUnits
from scripts.canonical_checkpoint import positive_number


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command',required=True)
    new = sub.add_parser('init'); new.add_argument('output',type=Path)
    new.add_argument('--purpose',required=True,choices=['conditional-research'])
    run = sub.add_parser('run'); run.add_argument('input',type=Path); run.add_argument('output',type=Path)
    run.add_argument('--duration-seconds',type=float,required=True); run.add_argument('--samples',type=int,required=True)
    run.add_argument('--trajectory',type=Path)
    export = sub.add_parser('export'); export.add_argument('input',type=Path); export.add_argument('output',type=Path)
    args = parser.parse_args(argv)
    outputs = [args.output]+([args.trajectory] if args.command=='run' and args.trajectory else [])
    resolved = [p.resolve() for p in outputs]
    if len(set(resolved))!=len(resolved) or any(p.exists() for p in resolved):
        raise ValueError('Distinct new output paths required; existing files are preserved')
    if args.command=='init':
        research.save(args.output,research.create(purpose=args.purpose))
    elif args.command=='run':
        positive_number(args.duration_seconds,'duration seconds')
        if args.samples<2: raise ValueError('At least two samples required')
        experiment = research.load(args.input); cp = experiment.checkpoint
        units = SIUnits(**{k:v for k,v in cp.metadata['units'].items() if k!='kind'})
        times = np.linspace(cp.time,cp.time+args.duration_seconds/units.time_s,args.samples)
        end, states = research.evolve(experiment,times); research.save(args.output,end)
        if args.trajectory:
            with args.trajectory.open('xb') as stream:
                np.savez_compressed(stream,times=times,states=states,
                    initial_receipt_sha256=experiment.receipt['payload_sha256'],
                    start_experiment_sha256=research.to_document(experiment)['payload_sha256'],
                    end_experiment_sha256=research.to_document(end)['payload_sha256'])
    else:
        text = json.dumps(research.velocity_export(research.load(args.input)),ensure_ascii=False,indent=2,allow_nan=False)+'\n'
        with args.output.open('x',encoding='utf-8',newline='\n') as stream: stream.write(text)
    print(str(args.output),'conditional-research; physical_mapping_certified=False',flush=True)


if __name__=='__main__': main()
