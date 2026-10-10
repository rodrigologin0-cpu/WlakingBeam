"""Cenários e varreduras. Não produz certificado de segurança operacional."""
from copy import deepcopy
from dataclasses import dataclass
import math
from .legacy import geometry
from .beam import Pad, solve_beam, UnsupportedEquilibrium
from .materials import Material, MissingMaterial

SCENARIOS = {'JSON original 591/340': (591.,340.),
             'Interface atual 720/490': (720.,490.),
             'Proposta 790/520': (790.,520.)}

@dataclass(frozen=True)
class Case:
    length_mm: float = 4560.
    width_mm: float | None = None
    thickness_mm: float | None = None
    temperature_c: float = 20.
    initial_temperature_c: float = 20.
    surface_temperature_c: float | None = None
    hours: float = 2.5
    section: int = 1
    scenario: str = 'Interface atual 720/490'
    mode: str = 'REF'
    drift_mm: float = 0.
    pad_mm: float = 100.
    moving_gap_mm: float = 20.
    disabled_fixed: tuple = ()
    expand: bool = False
    mirror: bool = False

    def __post_init__(self):
        for v in [self.length_mm,self.temperature_c,self.initial_temperature_c,self.hours,
                  self.drift_mm,self.pad_mm,self.moving_gap_mm]:
            if not math.isfinite(v): raise ValueError('Entradas devem ser finitas.')
        if self.length_mm<=0 or self.pad_mm<=0 or self.hours<0:
            raise ValueError('Comprimento/pad positivo e tempo não negativo são obrigatórios.')
        if self.surface_temperature_c is not None and not math.isfinite(self.surface_temperature_c):
            raise ValueError('Temperatura superficial deve ser finita.')
        for v in (self.width_mm,self.thickness_mm):
            if v is not None and (not math.isfinite(v) or v<=0):raise ValueError('Largura e espessura devem ser positivas e finitas.')
        if self.section not in (1,2,3): raise ValueError('Seção deve ser 1, 2 ou 3.')


def alignment(case):
    g=geometry(); family=deepcopy(g['BASE']['13'])
    family['p'],family['q']=SCENARIOS[case.scenario]
    ref,lo,hi=g['alignment'](family,case.length_mm,'13')
    return {'REF':ref,'MIN':lo,'MAX':hi}[case.mode], (ref,lo,hi)


def evaluate(case, material: Material | None, max_element_m=.15, pad_segments=2):
    g=geometry(); a,limits=alignment(case); a-=case.drift_mm
    if any(not isinstance(i,int) or i<1 or i>len(g['FIXED'][case.section]) for i in case.disabled_fixed):
        raise ValueError('Pad fixo perdido não existe na seção.')
    length=case.length_mm
    notes=['MIN/MAX: reconstrução geométrica existente; lógica real do PLC não fornecida.',
           'Limite operacional validado: indisponível.',
           'Transições longitudinais/colisão dinâmica: indeterminadas sem geometria e trajetória.']
    E=None
    if material is not None:
        E=material.modulus(case.temperature_c)
        if case.expand:
            strain=material.expansion(case.initial_temperature_c,case.temperature_c)
            if strain <= -1: raise ValueError('Dilatação inválida.')
            length*=1+strain
            notes.append('Dilatação longitudinal livre com extremidade esquerda ancorada em x; sem atrito/restrição axial.')
        elif case.temperature_c!=case.initial_temperature_c:
            notes.append('Dimensões mantidas nas informadas; dilatação não incluída.')
    if case.mirror: a=g['WIDTH']-a-length
    pads=[Pad(f'F{i}',(v-a)/1000,case.pad_mm/1000,0.,i not in case.disabled_fixed)
          for i,v in enumerate(g['FIXED'][case.section],1)]
    pads += [Pad(f'M{i}',(v-a)/1000,case.pad_mm/1000,case.moving_gap_mm/1000)
             for i,v in enumerate(g['MOVING'][case.section],1)]
    axes=[p.x_m*1000+a for p in pads if p.enabled]
    geo=g['support'](a,length,axes,case.pad_mm)
    out=dict(case=case,a_mm=a,length_mm=length,alignment_mm=limits,pads=pads,
             geometry=geo,
             geometry_fixed=g['support'](a,length,[p.x_m*1000+a for p in pads if p.enabled and p.name.startswith('F')],case.pad_mm),
             geometry_moving=g['support'](a,length,[p.x_m*1000+a for p in pads if p.enabled and p.name.startswith('M')],case.pad_mm),
             notes=notes,beam=None,status='Somente geometria',
             wall_clearance_mm=min(a-(35 if case.section==3 else 0),
                                   g['WIDTH']-(35 if case.section==3 else 0)-a-length))
    if material is None or case.width_mm is None or case.thickness_mm is None:
        notes.append('Ausência de material/dimensões: sem reações, flecha ou conclusão termomecânica.')
        return out
    # Massa conservada quando há expansão longitudinal (largura/espessura mantidas).
    density=material.density_kg_m3*case.length_mm/length
    try:
        out['beam']=solve_beam(length/1000,case.width_mm/1000,case.thickness_mm/1000,
                               E,density,pads,max_element_m,pad_segments)
        out['status']='Equilíbrio elástico calculado; sem validação operacional'
        notes.extend(out['beam'].warnings)
    except UnsupportedEquilibrium as exc:
        out['status']='Apoio insuficiente/marginal: '+str(exc)
    notes.append(f'Permanência {case.hours:g} h: não há evolução de fluência estrutural calculada.')
    if case.surface_temperature_c is not None:
        notes.append('Temperatura superficial registrada; gradiente pela espessura não resolvido e curvatura térmica não calculada.')
    return out


def drift_sweep(case,material,shifts):
    from dataclasses import replace
    return [evaluate(replace(case,drift_mm=float(x)),material) for x in shifts]


def lift_sweep(case,material,gaps):
    """Equilíbrios independentes; não simula impacto/velocidade/histerese."""
    from dataclasses import replace
    return [evaluate(replace(case,moving_gap_mm=float(x)),material) for x in gaps]


def thermal_history(case,material,samples):
    """Amostras (horas, T média, T superficial opcional), sem integração de fluência."""
    from dataclasses import replace
    last=-1.
    results=[]
    for row in samples:
        time=float(row['hours'])
        if not math.isfinite(time) or time<last or time<0:
            raise ValueError('Histórico requer tempos finitos, não negativos e ordenados.')
        last=time
        current=replace(case,hours=time,temperature_c=float(row['mean_c']),
                        surface_temperature_c=row.get('surface_c'))
        results.append(evaluate(current,material))
    return results


def geometric_intervals(rows):
    """Amostras admissíveis; não interpola fronteiras nem assegura operação."""
    return [r['case'].drift_mm for r in rows
            if all(r[key]['n']>=2 and r[key]['margin'] is not None and r[key]['margin']>0
                   for key in ('geometry_fixed','geometry_moving'))
            and r['wall_clearance_mm']>=0]


def calculated_intervals(rows,max_deflection_mm=None,max_stress_mpa=None,min_cg_margin_mm=None):
    if any(v is None for v in [max_deflection_mm,max_stress_mpa,min_cg_margin_mm]):
        return None  # limites de engenharia ainda ausentes
    if any(not math.isfinite(v) or v<=0 for v in [max_deflection_mm,max_stress_mpa]) or min_cg_margin_mm<0:
        raise ValueError('Limites de engenharia inválidos.')
    return [r['case'].drift_mm for r in rows if r['beam'] is not None
            and r['wall_clearance_mm']>=0
            and sum(v>r['beam'].total_weight_n*1e-8 for v in r['beam'].reactions_n.values())>=2
            and not any('Grandes deslocamentos' in w or 'Viga espessa' in w for w in r['beam'].warnings)
            and r['beam'].max_deflection_m*1000<=max_deflection_mm
            and r['beam'].stress_max_pa/1e6<=max_stress_mpa
            and r['beam'].cg_margin_m*1000>=min_cg_margin_mm]
