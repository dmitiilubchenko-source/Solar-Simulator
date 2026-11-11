"""Actual six-layout geometry and client-window screenshot at the failure."""
import json,sys
from pathlib import Path
import tkinter as tk
from solar_simulator.app import Laboratory
from solar_simulator.application_profiles import lunar_rotation
from solar_simulator.storage import to_document
W=Path('C:/Users/Admin/Documents/Codex/Solar408-20261111');label='408'
root=tk.Tk();obj=Laboratory(root,lunar_rotation());before=to_document(obj.experiment);rows=[];errors=[]
root.report_callback_exception=lambda *x:errors.append([str(v) for v in x])
root.tk.createcommand('capture408bg',lambda message,info:errors.append(dict(message=message,info=info)))
root.tk.eval('proc bgerror {message} {capture408bg $message $::errorInfo}')
def geometry(widget):
    return dict(name=str(widget),kind=widget.winfo_class(),mapped=bool(widget.winfo_ismapped()),x=widget.winfo_rootx(),y=widget.winfo_rooty(),width=widget.winfo_width(),height=widget.winfo_height(),required_width=widget.winfo_reqwidth(),required_height=widget.winfo_reqheight(),children=[geometry(w) for w in widget.winfo_children()])
try:
    for width,height in ((1180,820),(1024,768),(900,720)):
        root.geometry(f'{width}x{height}+40+40');root.update()
        for opened in (False,True):
            if opened:obj._toggle_settings();root.update()
            obj.canvas.draw();renderer=obj.canvas.get_renderer()
            rows.append(dict(width=width,height=height,settings_open=opened,scaling=float(root.tk.call('tk','scaling')),canvas_height=obj.canvas.get_tk_widget().winfo_height(),geometry=geometry(root),upper_label=list(obj.orbit.xaxis.label.get_window_extent(renderer).bounds),lower_title=list(obj.energy.title.get_window_extent(renderer).bounds),lower_label=list(obj.energy.xaxis.label.get_window_extent(renderer).bounds)))
            assert obj.canvas.get_tk_widget().winfo_height()>170
            assert to_document(obj.experiment)==before
        obj._toggle_settings();root.update()
finally:obj.close();root.tk.call('update')
with (W/(label+'-layout.json')).open('x',encoding='utf8') as f:json.dump(dict(rows=rows,background_errors=errors,state_unchanged=True),f,ensure_ascii=False,indent=2)
assert not errors,errors
print([(x['width'],x['settings_open'],x['canvas_height']) for x in rows],flush=True)
