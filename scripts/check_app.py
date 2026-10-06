"""Без диалогов: проверяет реальный Tk event loop и сохраняет демонстрацию."""
from pathlib import Path
import tkinter as tk

from solar_simulator.app import Laboratory
from solar_simulator.experiment import advance, preset


def main():
    root=tk.Tk()
    root.withdraw()
    app=Laboratory(root,advance(preset("sun-earth"),0))
    failures=[]
    initial_time=app.experiment.time
    def start():
        app._start()
    def finish():
        try:
            app._pause()
            if app.future is not None:
                root.after(50,finish)
                return
            assert app.experiment.time>initial_time
            target=Path("docs/laboratory-preview.png")
            app.figure.savefig(target,dpi=130)
            print(f"Tk worker/render OK: {app.experiment.time:.6g} s; {target}")
        except Exception as error:
            failures.append(error)
        finally:
            if app.future is None:
                app.close()
    root.after(100,start)
    root.after(2000,finish)
    root.mainloop()
    if failures:
        raise failures[0]


if __name__=="__main__":
    main()
