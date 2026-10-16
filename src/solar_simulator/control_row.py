"""Wrap complete control groups when the available width changes."""
from tkinter import ttk


class ControlRow(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.items = []
        self.pending = None
        self.bind("<Configure>", self._schedule)

    def add(self, widget):
        self.items.append(widget)
        widget.bind("<Map>", self._schedule, add="+")
        self._schedule()
        return widget

    def _schedule(self, event=None):
        if self.pending is None:
            self.pending = self.after_idle(self._layout)

    def _layout(self):
        self.pending = None
        width = max(1, self.winfo_width())
        x = y = row_height = 0
        for item in self.items:
            requested = min(item.winfo_reqwidth(), max(1,width-6))
            height = item.winfo_reqheight()
            if x and x+requested+6 > width:
                x = 0; y += row_height+6; row_height = 0
            item.place(x=x+3, y=y+3, width=requested, height=height)
            x += requested+6
            row_height = max(row_height, height)
        self.configure(height=y+row_height+6)
