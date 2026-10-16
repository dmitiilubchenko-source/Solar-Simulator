from pathlib import Path


def _check_responsive_controls(tmp_path):
    import tkinter as tk
    from solar_simulator.app import Laboratory
    from solar_simulator.application_profiles import lunar_rotation
    root=tk.Tk(); app=Laboratory(root,lunar_rotation())
    try:
        state=app.experiment
        for width,height in ((1180,820),(1024,768),(900,720)):
            root.geometry(f'{width}x{height}'); root.update()
            assert not app.settings_visible
            for expanded in (False,True):
                if expanded: app._toggle_settings(); root.update()
                bottom=root.winfo_rooty()+root.winfo_height()
                right=root.winfo_rootx()+root.winfo_width()
                for widget in app.actions+[app.pause_button,app.view_widget,app.reference_widget,app.details_widget]:
                    if widget.winfo_ismapped():
                        assert widget.winfo_rooty()+widget.winfo_height()<=bottom, (width,expanded,'height',widget)
                        assert widget.winfo_rootx()+widget.winfo_width()<=right, (width,expanded,'width',widget)
                        assert widget.winfo_width()>10, (width,expanded,'collapsed control',widget)
                        if widget in app.actions:
                            assert widget.winfo_width()>=widget.winfo_reqwidth(), (width,expanded,'clipped control',widget)
                assert app.details_widget.winfo_ismapped()
                assert app.canvas.get_tk_widget().winfo_height()>170, (width,expanded,'plot')
                app.canvas.draw()
                renderer=app.canvas.get_renderer()
                upper_label=app.orbit.xaxis.label.get_window_extent(renderer)
                lower_title=app.energy.title.get_window_extent(renderer)
                assert upper_label.y0>=lower_title.y1, (width,expanded,'overlapping graph labels')
                assert app.energy.xaxis.label.get_window_extent(renderer).y0>=0, (width,expanded,'clipped graph label')
                assert app.experiment is state
            app._toggle_settings(); root.update()
    finally: app.close()


def test_controls_and_footer_fit_three_window_sizes_with_open_and_closed_settings(tmp_path):
    from test_app_workflows import run_gui_check
    run_gui_check('_check_responsive_controls',tmp_path,Path(__file__).resolve())


def _check_fresh_diagnostics(tmp_path):
    import tkinter as tk
    from unittest.mock import patch
    import solar_simulator.app as application
    from solar_simulator.experiment import advance
    root=tk.Tk(); root.withdraw(); app=application.Laboratory(root)
    try:
        with patch('solar_simulator.app.report',wraps=application.report) as reports:
            app._set_experiment(advance(app.experiment,1))
            assert reports.call_count==1
            app._update_status(); assert reports.call_count==1
            assert app.energies[-1][0]==app.experiment.time
            app.experiment=advance(app.experiment,1)
            app._draw(); assert reports.call_count==2
            assert f"t = {app.experiment.time:.9g}" in app.status.get()
    finally: app.close()


def test_completed_frame_reuses_one_fresh_report_and_manual_redraw_recomputes(tmp_path):
    from test_app_workflows import run_gui_check
    run_gui_check('_check_fresh_diagnostics',tmp_path,Path(__file__).resolve())
