"""A cursor over verified recorded endpoints; elapsed wall time never reaches a solver."""
from math import isfinite


class Playback:
    def __init__(self,trajectory):
        self.trajectory=trajectory
        self.index=0
        self.running=False
        self._fraction=0.

    @property
    def state(self):
        return self.trajectory.frame(self.index)

    def seek(self,index):
        if type(index) is not int or not 0<=index<len(self.trajectory.times):
            raise ValueError('Снимок вне траектории')
        self.index=index;self.running=False;self._fraction=0.

    def play(self):
        self.running=self.index<len(self.trajectory.times)-1

    def pause(self):
        self.running=False

    def tick(self,elapsed,rate):
        if (type(elapsed) not in (int,float) or not isfinite(elapsed) or elapsed<0
                or type(rate) not in (int,float) or not isfinite(rate) or not 0<rate<=1000):
            raise ValueError('Просмотр: конечное время ≥0 и скорость (0,1000] снимков/с')
        if self.running:
            remaining=len(self.trajectory.times)-1-self.index
            # Avoid multiplying huge elapsed times once the end is already reached.
            progress=remaining if elapsed>=remaining/rate else self._fraction+elapsed*rate
            count=int(progress)
            self.index=min(self.index+count,len(self.trajectory.times)-1)
            self._fraction=progress-count
            if self.index==len(self.trajectory.times)-1:self.running=False
        return self.index
