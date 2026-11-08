"""Intentional failing teardown contract; standalone nonorbital reproducer.

Run with the qualified Python and --source pointing to exacta99worktree.
It is not included in normal pytest discovery and does not hide an xfail.
"""
import argparse,sys,time
from pathlib import Path
def reproduce(source):
 sys.path.insert(0,str(Path(source)/'src'))
 import tkinter as tk
 from solar_simulator.app import Laboratory
 root=tk.Tk();root.withdraw();errors=[]
 root.tk.createcommand('capture403',lambda message:errors.append(message))
 root.tk.eval('proc bgerror {message} {capture403 $message}')
 app=Laboratory(root);app.close()
 root.tk.call('update');time.sleep(.06);root.tk.call('update')
 assert not errors,repr(errors)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source',required=True);reproduce(p.parse_args().source)
