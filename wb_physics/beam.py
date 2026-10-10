"""Viga Hermite, pads rígidos finitos, solução convexa de contatos unilaterais.

SI, w positivo para baixo. Uma folga positiva é um pad abaixo do datum.
Não inclui plasticidade, fluência, atrito, dinâmica ou modelo de placa 2D.
"""
from dataclasses import dataclass
import math
import numpy as np
from scipy.linalg import solve

class UnsupportedEquilibrium(ValueError):
    pass

@dataclass(frozen=True)
class Pad:
    name: str
    x_m: float
    width_m: float
    gap_m: float = 0.0
    enabled: bool = True

@dataclass
class BeamResult:
    x_m: np.ndarray
    w_m: np.ndarray
    rotation: np.ndarray
    reactions_n: dict
    contact_x_m: np.ndarray
    contact_reactions_n: np.ndarray
    contact_gap_m: np.ndarray
    total_weight_n: float
    force_error_n: float
    moment_error_nm: float
    end_deflections_m: tuple
    max_deflection_m: float
    overhang_m: tuple
    cg_margin_m: float
    stress_max_pa: float
    warnings: list


def _bounded_quadratic(h, f, upper):
    """Primal active set; retained constraints remove rigid body modes.

    min .5 v'Hv - f'v, v <= upper. Return compressive duals f-Hv.
    """
    n = len(f)
    v = upper.copy()
    active = np.ones(n, dtype=bool)
    for _ in range(1000):
        free = ~active
        candidate = v.copy()
        if free.any():
            hf = h[np.ix_(free,free)]
            if np.linalg.eigvalsh(hf)[0] <= 1e-10 * max(1., np.linalg.norm(hf,2)):
                raise UnsupportedEquilibrium('Equilíbrio marginal: modo rígido livre; faltam apoios independentes.')
            candidate[free] = solve(hf, f[free] - h[np.ix_(free,active)] @ v[active], assume_a='sym')
        direction = candidate - v
        crossing = free & (candidate > upper + 1e-10)
        if crossing.any():
            ratios = np.full(n, np.inf)
            ratios[crossing] = (upper[crossing]-v[crossing])/direction[crossing]
            blocker = int(np.argmin(ratios))
            v += max(0.,min(1.,ratios[blocker])) * direction
            v[blocker] = upper[blocker]
            active[blocker] = True
            continue
        v = candidate
        reaction = f - h @ v
        bad = active & (reaction < -2e-8)
        if not bad.any():
            reaction[~active] = 0.
            if np.max(v-upper) > 1e-7:
                raise RuntimeError('Contato não convergiu: penetração residual.')
            return v, np.maximum(reaction,0.)
        remove = int(np.argmin(np.where(bad,reaction,np.inf)))
        active[remove] = False
    raise RuntimeError('Contato não convergiu em 1000 iterações.')


def solve_beam(length_m, width_m, thickness_m, modulus_pa, density_kg_m3, pads,
               max_element_m=0.15, pad_segments=2, gravity=9.80665):
    values = [length_m,width_m,thickness_m,modulus_pa,density_kg_m3,max_element_m,gravity]
    if any(not math.isfinite(v) or v <= 0 for v in values):
        raise ValueError('Dimensões, E, densidade, gravidade e malha devem ser positivos e finitos.')
    if not isinstance(pad_segments,int) or pad_segments < 1:
        raise ValueError('Discretização dos pads deve ter ao menos um segmento.')
    L=length_m
    locations={}
    for p in pads:
        if not all(math.isfinite(v) for v in [p.x_m,p.width_m,p.gap_m]) or p.width_m < 0:
            raise ValueError('Pad: posição/altura finita e largura não negativa obrigatórias (zero = apoio ideal).')
        if not p.enabled: continue
        lo,hi=max(0.,p.x_m-p.width_m/2),min(L,p.x_m+p.width_m/2)
        if p.width_m == 0:
            if not 0 <= p.x_m <= L: continue
            points = [p.x_m]
        else:
            if hi-lo <= 1e-10: continue
            points = np.linspace(lo,hi,pad_segments+1)
        for x in points:
            key=round(float(x),11)
            if key in locations:
                raise ValueError('Pads sobrepostos não suportados; revise a geometria.')
            locations[key]=(p.name,p.gap_m)
    if len(locations)<2:
        raise UnsupportedEquilibrium('Sem dois pontos de apoio distintos sobre a placa.')
    supports=sorted(locations)
    if not supports[0]+1e-10 < L/2 < supports[-1]-1e-10:
        raise UnsupportedEquilibrium('CG fora do envelope dos apoios: peso próprio não tem equilíbrio estável.')
    # Não criar elementos quase nulos entre grade regular e bordas de pad.
    # A posição real do contato sempre prevalece sobre a grade auxiliar.
    grid=np.linspace(0,L,max(2,math.ceil(L/max_element_m))+1)
    separation=min(.002,max_element_m*.05)
    background=[round(float(x),11) for x in grid[1:-1]
                if min(abs(x-s) for s in supports)>separation]
    nodes=np.array(sorted(set([0.,round(L,11)] + background + supports)))
    x=nodes/L
    nd=2*len(x)
    K=np.zeros((nd,nd)); f=np.zeros(nd)
    for i,ell in enumerate(np.diff(x)):
        ids=np.arange(2*i,2*i+4)
        ke=np.array([[12,6*ell,-12,6*ell],[6*ell,4*ell**2,-6*ell,2*ell**2],
                     [-12,-6*ell,12,-6*ell],[6*ell,2*ell**2,-6*ell,4*ell**2]])/ell**3
        K[np.ix_(ids,ids)] += ke
        f[ids] += np.array([ell/2,ell**2/12,ell/2,-ell**2/12])
    support_ids=np.array([2*int(np.argmin(abs(nodes-s))) for s in supports])
    rest=np.setdiff1d(np.arange(nd),support_ids)
    Kff=K[np.ix_(rest,rest)]
    Kfs=K[np.ix_(rest,support_ids)]
    inverse_parts=solve(Kff,np.column_stack([Kfs,f[rest]]),assume_a='sym')
    H=K[np.ix_(support_ids,support_ids)]-Kfs.T @ inverse_parts[:,:-1]
    H=(H+H.T)/2
    F=f[support_ids]-Kfs.T @ inverse_parts[:,-1]
    I=width_m*thickness_m**3/12
    q=density_kg_m3*width_m*thickness_m*gravity
    deflection_scale=q*L**4/(modulus_pa*I)
    gaps=np.array([locations[s][1] for s in supports])
    vs,dual=_bounded_quadratic(H,F,gaps/deflection_scale)
    u=np.zeros(nd); u[support_ids]=vs
    u[rest]=inverse_parts[:,-1]-inverse_parts[:,:-1] @ vs
    w=u[::2]*deflection_scale
    theta=u[1::2]*deflection_scale/L
    R=dual*q*L
    weight=q*L
    force_error=float(R.sum()-weight)
    moment_error=float(R @ np.array(supports)-weight*L/2)
    if abs(force_error)>weight*1e-5 or abs(moment_error)>weight*L*1e-5:
        raise RuntimeError('Equilíbrio não convergiu dentro da tolerância; resultado recusado.')
    sample_x=[]; sample_w=[]; curvatures=[]
    for i,ell in enumerate(np.diff(x)):
        for t in np.linspace(0,1,9):
            N=np.array([1-3*t*t+2*t**3,ell*(t-2*t*t+t**3),3*t*t-2*t**3,ell*(-t*t+t**3)])
            B=np.array([-6+12*t,ell*(-4+6*t),6-12*t,ell*(-2+6*t)])/ell**2
            ue=u[2*i:2*i+4]
            sample_x.append((x[i]+t*ell)*L); sample_w.append(N @ ue*deflection_scale)
            curvatures.append(B @ ue*deflection_scale/L**2)
    contact=R>weight*1e-8
    actual=np.array(supports)[contact]
    if len(actual)<2:
        raise UnsupportedEquilibrium('Sustentação marginal ou concentrada em um ponto.')
    reactions={p.name:0. for p in pads}
    for s,r in zip(supports,R): reactions[locations[s][0]]+=float(r)
    warnings=[]
    if sum(r>weight*1e-8 for r in reactions.values())<=1:
        warnings.append('Carga concentrada em um único pad; estabilidade local não validada.')
    if L/thickness_m<10:
        warnings.append('Viga espessa: deformação por cisalhamento pode ser relevante.')
    if max(abs(np.asarray(sample_w)))/L>0.02 or max(abs(theta))>0.1:
        warnings.append('Grandes deslocamentos/rotações: modelo linear fora do regime recomendado.')
    warnings += ['Tensões elásticas não comparadas à resistência/plasticidade do aço.',
                 'Sem fluência acoplada: tempo não altera a solução elástica.']
    return BeamResult(np.array(sample_x),np.array(sample_w),theta,reactions,np.array(supports),R,
                      gaps-vs*deflection_scale,weight,force_error,moment_error,
                      (float(w[0]),float(w[-1])),float(max(abs(np.asarray(sample_w)))),
                      (float(actual.min()),float(L-actual.max())),
                      float(min(L/2-actual.min(),actual.max()-L/2)),
                      float(max(abs(np.asarray(curvatures)))*modulus_pa*thickness_m/2),warnings)
