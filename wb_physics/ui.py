"""Aba adicional; mantém todos os controles do estudo geométrico original."""
import json
import threading
import queue
from dataclasses import replace, asdict
from pathlib import Path
import numpy as np
from .analysis import Case, SCENARIOS, evaluate, drift_sweep, lift_sweep, thermal_history, geometric_intervals, calculated_intervals
from .materials import Material
from .creep import NortonParameters

class ThermomechanicalTab:
    def __init__(self,parent):
        import tkinter as tk
        from tkinter import ttk
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        self.tk=tk;self.ttk=ttk;self.parent=parent
        self.material=None; self.histories={};self.creep=None;self.last=None
        shell=ttk.Panedwindow(parent,orient='horizontal');shell.pack(fill='both',expand=True)
        left=ttk.Frame(shell,width=325);right=ttk.Frame(shell);shell.add(left,weight=0);shell.add(right,weight=1)
        sc=tk.Canvas(left,width=320,highlightthickness=0)
        scrollbar=ttk.Scrollbar(left,orient='vertical',command=sc.yview)
        sc.configure(yscrollcommand=scrollbar.set);scrollbar.pack(side='right',fill='y');sc.pack(fill='both',expand=True)
        form=ttk.Frame(sc,padding=9);sc.create_window((0,0),window=form,anchor='nw')
        form.bind('<Configure>',lambda _: sc.configure(scrollregion=sc.bbox('all')))
        ttk.Label(form,text='SUSTENTAÇÃO TERMOMECÂNICA',font=('Arial',11,'bold')).pack(anchor='w')
        ttk.Label(form,text='Família 13 · SI interno · dados não presumidos',wraplength=290).pack(anchor='w')
        self.vars={}
        fields=[('scenario','Referências de alinhamento',list(SCENARIOS)[1],list(SCENARIOS)),
                ('mode','Envelope existente (não validado PLC)','REF',['MIN','REF','MAX']),
                ('section','Seção','1',['1','2','3']),
                ('length','Comprimento (mm)','4560',['4500','4560','4780','4860']),
                ('width','Largura (750–1950 mm)','750',None),
                ('thickness','Espessura (mm)','200',['200','225','250']),
                ('temperature','Temperatura média (°C) — informar','20',None),
                ('initial','Temperatura inicial (°C) — informar','20',None),
                ('surface','Temperatura superficial (°C), opcional','',None),
                ('hours','Permanência (h)','2.5',None),
                ('gap','Móvel abaixo da fixa (mm)','20',None),
                ('drift','Deslocamento para parede (+), mm','0',None),
                ('pad','Largura efetiva do pad (mm)','100',None),
                ('disabled','Pads fixos perdidos: números separados por vírgula','',None),
                ('sweep','Amplitude da varredura ± (mm)','150',None),
                ('grade','Steel Grade / classe (informar grau)','Baixo carbono (grau não informado)',None),
                ('source','Fonte de E e densidade (obrigatória)','',None),
                ('density','Densidade (kg/m³), sem padrão','',None),
                ('modulus','E na temperatura média (GPa), sem padrão','',None),
                ('max_w','Limite de flecha (mm), opcional','',None),
                ('max_stress','Limite elástico admissível (MPa), opcional','',None),
                ('min_margin','Margem mínima do CG (mm), opcional','',None)]
        for key,label,value,choices in fields:
            ttk.Label(form,text=label,wraplength=290).pack(anchor='w',pady=(5,0))
            var=tk.StringVar(value=value);self.vars[key]=var
            widget=ttk.Combobox(form,textvariable=var,values=choices,width=33,state='readonly' if key in ('mode','section','scenario','thickness') else 'normal') if choices else ttk.Entry(form,textvariable=var,width=36)
            widget.pack(anchor='w')
        self.expand=tk.BooleanVar(value=False);self.mirror=tk.BooleanVar(value=False)
        ttk.Checkbutton(form,text='Dilatação longitudinal (requer alpha(T))',variable=self.expand).pack(anchor='w',pady=5)
        ttk.Checkbutton(form,text='Analisar placa espelhada',variable=self.mirror).pack(anchor='w')
        ttk.Button(form,text='Carregar material / histórico JSON',command=self.load_material).pack(fill='x',pady=5)
        self.button=ttk.Button(form,text='Calcular / comparar / varrer',command=self.calculate);self.button.pack(fill='x',pady=3)
        ttk.Button(form,text='Exportar relatório JSON + gráfico',command=self.export).pack(fill='x',pady=3)
        self.status=tk.StringVar(value='Somente geometria até informar material rastreável. Nenhum limite operacional validado.')
        ttk.Label(right,textvariable=self.status,wraplength=950,foreground='#8a3500').pack(fill='x',padx=6,pady=5)
        self.figure=Figure(figsize=(11,7),dpi=85)
        self.canvas=FigureCanvasTkAgg(self.figure,master=right);self.canvas.get_tk_widget().pack(fill='both',expand=True)
        self.report=tk.Text(right,height=10,wrap='word');self.report.pack(fill='x',padx=6,pady=4)
        self._set_report('Selecione o cenário e informe E(T), densidade e fonte, ou carregue uma tabela.\n'
                         'Sem fluência acoplada, 2–3 horas não permitem prever deformação permanente.\n'
                         'MIN/MAX preserva a reconstrução existente; a lógica real do PLC ainda é necessária.')

    def _set_report(self,text):
        self.report.configure(state='normal');self.report.delete('1.0','end');self.report.insert('1.0',text);self.report.configure(state='disabled')

    def load_material(self):
        from tkinter import filedialog,messagebox
        p=filedialog.askopenfilename(filetypes=[('Dados materiais JSON','*.json')])
        if not p:return
        try:
            data=json.loads(Path(p).read_text(encoding='utf-8'))
            material=Material.from_dict(data.get('material',data))
            histories=data.get('thermal_history_by_section',{})
            for section,samples in histories.items():
                if str(section) not in ('1','2','3'): raise ValueError('Histórico: seção deve ser 1, 2 ou 3.')
                # Validação de estrutura, não presume grade/temperaturas de dados não fornecidos.
                for row in samples: float(row['hours']);float(row['mean_c'])
            creep=NortonParameters(**data['creep']) if data.get('creep') else None
            if creep and creep.grade != material.grade: raise ValueError('Fluência e material devem usar o mesmo Steel Grade.')
            self.material=material;self.histories=histories;self.creep=creep
            self.vars['grade'].set(material.grade);self.vars['source'].set(material.source)
            self.vars['density'].set(str(material.density_kg_m3));self.vars['modulus'].set('')
            self.status.set('Tabela carregada; não há extrapolação. '+material.source)
        except (ValueError,KeyError,TypeError,OSError) as e:messagebox.showerror('Dados inválidos',str(e))

    def inputs(self):
        v={k:x.get().strip() for k,x in self.vars.items()}
        optional=lambda key:float(v[key]) if v[key] else None
        disabled=tuple(int(x.strip()) for x in v['disabled'].split(',') if x.strip())
        section=int(v['section'])
        from .legacy import geometry
        if any(i<1 or i>len(geometry()['FIXED'][section]) for i in disabled):raise ValueError('Número de pad fixo inexistente na seção.')
        width=optional('width');thickness=optional('thickness')
        if width is not None and not 750<=width<=1950:raise ValueError('Largura fornecida para este estudo: 750–1950 mm.')
        case=Case(length_mm=float(v['length']),width_mm=width,thickness_mm=thickness,
                  temperature_c=float(v['temperature']),initial_temperature_c=float(v['initial']),
                  surface_temperature_c=optional('surface'),hours=float(v['hours']),section=section,
                  scenario=v['scenario'],mode=v['mode'],drift_mm=float(v['drift']),pad_mm=float(v['pad']),
                  moving_gap_mm=float(v['gap']),disabled_fixed=disabled,expand=self.expand.get(),mirror=self.mirror.get())
        material=self.material
        if v['modulus'] or (v['density'] and not material):
            if not v['modulus'] or not v['density']: raise ValueError('Informe E e densidade conjuntamente, ou carregue tabela.')
            material=Material(v['grade'],v['source'],float(v['density']),((case.temperature_c,float(v['modulus'])*1e9),))
        elif material and (v['grade']!=material.grade or v['source']!=material.source or float(v['density'])!=material.density_kg_m3):
            raise ValueError('Dados diferem da tabela: recarregue material ou informe E explícito.')
        span=float(v['sweep'])
        if not np.isfinite(span) or span<=0 or span>3000:raise ValueError('Amplitude de varredura: 0 < valor ≤ 3000 mm.')
        return case,material,span,(optional('max_w'),optional('max_stress'),optional('min_margin'))

    def calculate(self):
        from tkinter import messagebox
        try:case,material,span,limits=self.inputs()
        except (ValueError,KeyError,TypeError) as e:messagebox.showerror('Entradas',str(e));return
        self.button.configure(state='disabled');self.status.set('Resolvendo equilíbrios e varreduras…')
        delivery=queue.Queue()
        def poll():
            try: result,error=delivery.get_nowait()
            except queue.Empty:
                self.parent.after(100,poll);return
            if error is not None:self.failed(error)
            else:self.display(result)
        def work():
            try:
                main=evaluate(case,material)
                drift=drift_sweep(case,material,np.linspace(case.drift_mm-span,case.drift_mm+span,21))
                lift=lift_sweep(case,material,np.linspace(20,-20,9))
                comparisons=[evaluate(replace(case,length_mm=L,scenario=s,mode=mode),material)
                             for s in SCENARIOS for L in (4500,4560,4780,4860) for mode in ('MIN','REF','MAX')]
                sections=[evaluate(replace(case,section=s,disabled_fixed=case.disabled_fixed if s==case.section else ()),material) for s in (1,2,3)]
                samples=self.histories.get(str(case.section)) or [{'hours':h,'mean_c':case.temperature_c} for h in sorted(set([0.,2.,3.,case.hours]))]
                history=thermal_history(case,material,samples)
                temperatures=[evaluate(replace(case,temperature_c=t),material) for t,_ in material.elastic_table] if material else []
                result=dict(main=main,drift=drift,lift=lift,comparisons=comparisons,sections=sections,history=history,
                            temperatures=temperatures,geometric_samples=geometric_intervals(drift),
                            elastic_samples=calculated_intervals(drift,*limits),material=material)
                delivery.put((result,None))
            except Exception as exc:
                delivery.put((None,str(exc)))
        threading.Thread(target=work,daemon=True).start()
        self.parent.after(100,poll)

    def failed(self,message):
        self.button.configure(state='normal');self.status.set('Cálculo interrompido: '+message)
        self._set_report('Não há resultado válido para esta entrada.\n'+message)

    def display(self,result):
        self.last=result;self.button.configure(state='normal')
        row=result['main'];beam=row['beam'];self.status.set(row['status'])
        self.figure.clear();axes=self.figure.subplots(2,3)
        ax=axes[0,0];ax.set_title('Placa / pads (mm) — deformação ampliada')
        L=row['length_mm']; ax.plot([0,L],[0,0],color='#bbb')
        scale=1.
        if beam:
            scale=max(1.,0.05*L/max(beam.max_deflection_m*1000,1e-6))
            ax.plot(beam.x_m*1000,-beam.w_m*1000*scale,color='#c6670a',label=f'Escala vertical ×{scale:.1f}')
        for p in row['pads']:
            if p.x_m*1000+p.width_m*500<0 or p.x_m*1000-p.width_m*500>L:continue
            r=beam.reactions_n.get(p.name,0) if beam else 0
            ax.plot([p.x_m*1000-p.width_m*500,p.x_m*1000+p.width_m*500],[-p.gap_m*1000*scale]*2,
                    color='#148548' if r>0 else '#888',lw=4,ls='-' if p.enabled else ':')
            ax.annotate(f'{p.name}\n{r/1000:.1f} kN' if beam else p.name,(p.x_m*1000,-p.gap_m*1000*scale),fontsize=7)
        ax.set_xlabel('x local (mm)');ax.set_ylabel('vertical ampliada (mm)');
        if beam:ax.legend(fontsize=7)
        ax=axes[0,1];ax.set_title('Flecha × tempo — somente elasticidade')
        history=result['history'];ax.plot([r['case'].hours for r in history],[r['beam'].max_deflection_m*1000 if r['beam'] else np.nan for r in history],'o-')
        ax.set_xlabel('h');ax.set_ylabel('Flecha máx. absoluta (mm)')
        ax=axes[0,2];ax.set_title('Flecha × T — pontos materiais fornecidos')
        temp=result['temperatures'];ax.plot([r['case'].temperature_c for r in temp],[r['beam'].max_deflection_m*1000 if r['beam'] else np.nan for r in temp],'o-');ax.set_xlabel('T média (°C)');ax.set_ylabel('mm')
        drift=result['drift'];shifts=[r['case'].drift_mm for r in drift]
        ax=axes[1,0];ax.set_title('Reações × deslocamento')
        if beam:
            for name in beam.reactions_n:
                values=[r['beam'].reactions_n.get(name,0)/1000 if r['beam'] else np.nan for r in drift]
                if any(np.isfinite(v) and v>0 for v in values):ax.plot(shifts,values,label=name)
            ax.legend(fontsize=6,ncol=2)
        ax.set_xlabel('Deslocamento para parede (+), mm');ax.set_ylabel('kN')
        ax=axes[1,1];ax.set_title('Overhang e margem CG × deslocamento')
        for label,get in [('OH esquerdo',lambda r:r['beam'].overhang_m[0]*1000),('OH direito',lambda r:r['beam'].overhang_m[1]*1000),('Margem CG',lambda r:r['beam'].cg_margin_m*1000)]:
            ax.plot(shifts,[get(r) if r['beam'] else np.nan for r in drift],label=label)
        ax.legend(fontsize=6);ax.set_xlabel('mm');ax.set_ylabel('mm')
        ax=axes[1,2];ax.set_title('Alinhamentos / envelope MIN–MAX')
        for scenario in SCENARIOS:
            rows=[r for r in result['comparisons'] if r['case'].scenario==scenario]
            refs=[r for r in rows if r['case'].mode=='REF']; ax.plot([r['case'].length_mm for r in refs],[r['a_mm'] for r in refs],'o-',label=scenario)
            ax.fill_between([r['case'].length_mm for r in refs],[next(r['a_mm'] for r in rows if r['case'].length_mm==x['case'].length_mm and r['case'].mode=='MIN') for x in refs],
                            [next(r['a_mm'] for r in rows if r['case'].length_mm==x['case'].length_mm and r['case'].mode=='MAX') for x in refs],alpha=.1)
        ax.legend(fontsize=6);ax.set_xlabel('Comprimento (mm)');ax.set_ylabel('Posição efetiva (mm)')
        for ax in axes.flat:ax.grid(alpha=.15)
        self.figure.tight_layout();self.canvas.draw_idle()
        lines=[f"Seção {row['case'].section}; {row['case'].scenario}; {row['case'].mode}; posição {row['a_mm']:.2f} mm.",
               f"Folga lateral mínima: {row['wall_clearance_mm']:.2f} mm."]
        if beam:
            lines += [f'Peso: {beam.total_weight_n/1000:.3f} kN; residual forças {beam.force_error_n:.4g} N; momentos {beam.moment_error_nm:.4g} N·m.',
                      f'Flecha extremidades: {beam.end_deflections_m[0]*1000:.3f} / {beam.end_deflections_m[1]*1000:.3f} mm; máxima {beam.max_deflection_m*1000:.3f} mm.',
                      f'Tensão elástica máxima: {beam.stress_max_pa/1e6:.3f} MPa (não equivale a tensão admissível).',
                      'Reações: '+', '.join(f'{name}={r/1000:.2f} kN' for name,r in beam.reactions_n.items())]
            if self.creep and result['material'] and self.creep.grade==result['material'].grade:
                try:
                    strain=self.creep.constant_stress_strain(beam.stress_max_pa,row['case'].temperature_c,row['case'].hours)
                    lines.append(f'Norton em tensão constante: ε={strain:.3g}; fonte {self.creep.source}. NÃO é flecha nem redistribuição de contatos.')
                except ValueError as e:lines.append('Fluência constitutiva indisponível: '+str(e))
        lines.append(f"Geometria por grupo: fixas {row['geometry_fixed']['n']} pads; móveis {row['geometry_moving']['n']} pads (sobreposição não garante contato vertical).")
        lines.append('Retomada quase-estática, sem impacto:')
        for r in result['lift']:
            b=r['beam']; moving=sum(v for k,v in b.reactions_n.items() if k.startswith('M'))/1000 if b else None
            lines.append(f"  Móvel abaixo {r['case'].moving_gap_mm:g} mm: carga móvel {moving:.2f} kN" if moving is not None else f"  {r['case'].moving_gap_mm:g} mm: {r['status']}")
        lines.append('Seções calculadas independentemente (não simula transição longitudinal):')
        lines.extend(f"  S{r['case'].section}: {r['status']}" for r in result['sections'])
        lines.append('Limite geométrico: amostras com CG interno e ≥2 pads em cada grupo fixo/móvel '+str(result['geometric_samples'])+' mm (fronteiras não refinadas).')
        lines.append('Limite termomecânico elástico: '+('indeterminado — faltam limites de engenharia.' if result['elastic_samples'] is None else str(result['elastic_samples'])+' mm, sem fluência/plasticidade.'))
        lines.extend(row['notes']);self._set_report('\n'.join(lines))

    def export(self):
        from tkinter import filedialog,messagebox
        if self.last is None:messagebox.showinfo('Relatório','Execute uma análise primeiro.');return
        p=filedialog.asksaveasfilename(defaultextension='.json',filetypes=[('Relatório JSON','*.json')])
        if not p:return
        def encode(obj):
            if isinstance(obj,np.ndarray):return obj.tolist()
            if hasattr(obj,'__dataclass_fields__'):return asdict(obj)
            raise TypeError(type(obj).__name__)
        try:
            Path(p).write_text(json.dumps(self.last,ensure_ascii=False,indent=2,default=encode,allow_nan=False),encoding='utf-8')
            self.figure.savefig(str(Path(p).with_suffix('.png')),dpi=180)
            Path(p).with_suffix('.txt').write_text(self.report.get('1.0','end'),encoding='utf-8')
        except (OSError,ValueError,TypeError) as e:messagebox.showerror('Exportação',str(e))
