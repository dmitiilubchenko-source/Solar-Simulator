"""Update saved orbital snapshots without rebuilding axes or static artists."""
import numpy as np
from matplotlib import rcParams
from matplotlib.collections import LineCollection
from matplotlib.lines import Line2D
from matplotlib.transforms import Bbox

from .orbit_view import trajectory_data


class PlotArtists:
    def __init__(self,orbit,energy):
        self.orbit,self.energy=orbit,energy
        self.paths=LineCollection([],linewidths=1)
        orbit.add_collection(self.paths)
        self.markers=orbit.scatter([],[],s=36,zorder=3)
        self.balance,=energy.plot([],[],color="#b35c1e")
        self.legend_key=None

    def update(self,frames,names,reference,axes,energies):
        visible,paths,markers=trajectory_data(frames,names,reference,axes)
        palette=rcParams['axes.prop_cycle'].by_key()['color']
        indices={name:index for index,name in enumerate(names)}
        colors=[palette[indices[name]%len(palette)] for name in visible]
        self.paths.set_segments(paths);self.paths.set_color(colors)
        self.markers.set_offsets(markers);self.markers.set_facecolor(colors)
        key=(tuple(names),tuple(visible),reference,tuple(colors))
        if key!=self.legend_key:
            legend=self.orbit.get_legend()
            if legend is not None:legend.remove()
            if paths:
                handles=[Line2D([],[],color=color,linewidth=1,label=name)
                         for name,color in zip(visible,colors)
                         if len(names)<=40 or indices[name]<12 or name==reference]
                self.orbit.legend(handles=handles,loc='upper right',fontsize=8)
            self.legend_key=key
        # Collections are not covered by Axes.relim; reset their data limits.
        if paths:
            self.orbit.dataLim=Bbox.null()
            self.orbit.update_datalim(np.concatenate(paths,axis=0))
        else:
            self.orbit.set_xlim(0,1);self.orbit.set_ylim(0,1)
        self.orbit.set_autoscalex_on(True);self.orbit.set_autoscaley_on(True)
        if paths:self.orbit.autoscale_view()
        self.balance.set_data([p[0] for p in energies],[p[1] for p in energies])
        if energies:self.energy.relim()
        self.energy.set_autoscalex_on(True);self.energy.set_autoscaley_on(True)
        self.energy.autoscale_view()
        return visible,paths,markers
