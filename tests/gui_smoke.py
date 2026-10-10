"""Teste funcional Tk; usa display real Windows ou DISPLAY virtual Linux."""
import json
import tempfile
import time
from pathlib import Path
from unittest.mock import patch
from wb_physics.legacy import geometry
from wb_physics.materials import Material


def run():
    g=geometry()
    with tempfile.TemporaryDirectory(prefix='wb-gui-') as folder:
        folder=Path(folder)
        for physical in (False,True):
            app=g['App'](enable_thermomechanical=physical)
            try:
                app.root.update()
                assert app.families['13']['p']==720 and app.families['13']['q']==490
                for family in ('1','2','13'):
                    app.family.set(family);app.change_family();app.root.update()
                    assert app.data['family']==family
                app.family.set('13');app.change_family()
                app.mode.set('MANUAL');app.vars['manual'].set('1125');app.update();app.root.update()
                assert app.data['a']==1125
                params=folder/'parameters.json'
                with patch('tkinter.filedialog.asksaveasfilename',return_value=str(params)):app.save()
                assert params.exists()
                app.vars['manual'].set('1000')
                with patch('tkinter.filedialog.askopenfilename',return_value=str(params)):app.load()
                assert app.vars['manual'].get()=='1125'
                for fmt in ('pdf','svg','png'):
                    path=folder/f'legacy-{physical}.{fmt}'
                    with patch('tkinter.filedialog.asksaveasfilename',return_value=str(path)):app.export()
                    assert path.stat().st_size>1000
                if physical:
                    assert len(app.tabs.tabs())==2
                    tab=app.thermomechanical
                    fixture={'grade':'FIXTURE SINTÉTICA — NÃO OPERACIONAL','source':'Teste funcional; não aço real',
                             'density_kg_m3':7800,'elastic_table':[[20,200e9],[1000,80e9]],
                             'expansion_table':[[20,1e-5],[1000,1e-5]]}
                    material_file=folder/'fixture-material.json';material_file.write_text(json.dumps(fixture))
                    with patch('tkinter.filedialog.askopenfilename',return_value=str(material_file)):tab.load_material()
                    tab.vars['temperature'].set('1000');tab.vars['thickness'].set('225');tab.vars['width'].set('1950')
                    tab.calculate()
                    deadline=time.monotonic()+60
                    while tab.last is None and time.monotonic()<deadline:
                        app.root.update();time.sleep(.02)
                        if tab.status.get().startswith('Cálculo interrompido:'):raise AssertionError(tab.status.get())
                    assert tab.last is not None,'Timeout na análise gráfica'
                    assert tab.last['main']['beam'] is not None
                    assert len(tab.last['comparisons'])==36 and len(tab.last['drift'])==21
                    assert len(tab.last['sections'])==3
                    result=folder/'analysis.json'
                    with patch('tkinter.filedialog.asksaveasfilename',return_value=str(result)):tab.export()
                    report=json.loads(result.read_text())
                    assert report['main']['beam']['total_weight_n']>0
                    assert report['main']['case']['width_mm']==1950
                    assert result.with_suffix('.png').stat().st_size>1000
                    assert 'Limite termomecânico' in result.with_suffix('.txt').read_text()
                    # Os novos cálculos não modificam os parâmetros geométricos.
                    assert app.vars['manual'].get()=='1125'
            finally:
                for timer in app.root.tk.call('after','info'):
                    app.root.tk.call('after','cancel',timer)
                app.root.destroy()
    print('PASS: GUI geométrica e nova aba, salvar/abrir JSON, exportar PDF/SVG/PNG, cálculo e relatório.')

if __name__=='__main__':run()
