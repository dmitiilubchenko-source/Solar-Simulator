"""Fresh-process research checkpoint continuation; exclusive output files."""
import argparse
from pathlib import Path
import sys
import os

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
from scripts.relative_canonical_checkpoint import load,save,evolve,REPRESENTATION


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',required=True);parser.add_argument('--times',required=True)
    parser.add_argument('--checkpoint-output',required=True);parser.add_argument('--trajectory-output',required=True)
    args = parser.parse_args()
    outputs = [Path(args.checkpoint_output),Path(args.trajectory_output)]
    if outputs[0].resolve()==outputs[1].resolve() or any(p.exists() for p in outputs):
        raise FileExistsError('Distinct new output paths required')
    cp = load(args.input)
    with np.load(args.times,allow_pickle=False) as archive:times = archive['times'].copy()
    end,states = evolve(cp,times,source_root=ROOT)
    save(outputs[0],end)
    with outputs[1].open('xb') as stream:np.savez_compressed(stream,times=times,states=states,
        representation=REPRESENTATION,process_id=os.getpid())
    print('Relative canonical continuation complete',flush=True)


if __name__=='__main__':main()
