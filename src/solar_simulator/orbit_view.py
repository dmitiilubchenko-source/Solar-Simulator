"""Project saved snapshots; rendering never changes the physical experiment."""
import numpy as np
from matplotlib import rcParams
from matplotlib.collections import LineCollection
from matplotlib.lines import Line2D


def trajectory_data(frames, names, reference, axes):
    x,y=axes
    if frames and names:
        required=list(names)
        if reference is not None and reference not in required:
            required.append(reference)
        try:
            positions=np.asarray([[frame[name] for name in required] for frame in frames],dtype=float)
        except KeyError:
            # Mergers change membership. Keep each historical track's valid snapshots.
            pass
        else:
            projected=positions[:,:len(names),:][...,[x,y]]
            if reference is not None:
                center=positions[:,required.index(reference),:][:,[x,y]]
                projected=projected-center[:,None,:]
            paths=[projected[:,index,:] for index in range(len(names))]
            return list(names),paths,projected[-1,:,:].copy()
    visible=[]; paths=[]
    for name in names:
        points=[(frame[name][x]-(frame[reference][x] if reference is not None else 0),
                 frame[name][y]-(frame[reference][y] if reference is not None else 0))
                for frame in frames if name in frame and (reference is None or reference in frame)]
        if points:
            visible.append(name); paths.append(np.asarray(points,dtype=float))
    markers=np.asarray([path[-1] for path in paths],dtype=float).reshape(-1,2)
    return visible,paths,markers


def draw_orbits(axis, frames, names, reference, axes):
    visible,paths,markers=trajectory_data(frames,names,reference,axes)
    palette=rcParams['axes.prop_cycle'].by_key()['color']
    indices={name:index for index,name in enumerate(names)}
    colors=[palette[indices[name]%len(palette)] for name in visible]
    if paths:
        axis.add_collection(LineCollection(paths,colors=colors,linewidths=1))
        axis.scatter(markers[:,0],markers[:,1],s=36,c=colors,zorder=3)
        axis.autoscale_view()
        handles=[Line2D([],[],color=color,linewidth=1,label=name) for name,color in zip(visible,colors)
                 if len(names)<=40 or indices[name]<12 or name==reference]
        axis.legend(handles=handles,loc='upper right',fontsize=8)
    return visible,paths,markers
