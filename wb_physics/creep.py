"""Norton-Arrhenius em tensão constante; etapa constitutiva, não solver de viga.

εdot = A |σ|^n exp(-Q/(R T)) sign(σ).
A em Pa^(-n)/s, Q em J/mol, T em K. Sem valores padrão, sem acoplamento estrutural.
"""
from dataclasses import dataclass
import math

@dataclass(frozen=True)
class NortonParameters:
    grade: str
    source: str
    A_pa_n_s: float
    n: float
    Q_j_mol: float
    temperature_range_c: tuple
    stress_range_pa: tuple

    def __post_init__(self):
        if not isinstance(self.grade,str) or not isinstance(self.source,str) or not self.grade.strip() or not self.source.strip():
            raise ValueError('Fluência requer grade e fonte explícitos.')
        if len(self.temperature_range_c)!=2 or len(self.stress_range_pa)!=2:
            raise ValueError('Faixas constitutivas requerem limites inferior/superior.')
        values=[self.A_pa_n_s,self.n,self.Q_j_mol,*self.temperature_range_c,*self.stress_range_pa]
        if not all(isinstance(v,(int,float)) and math.isfinite(v) for v in values):
            raise ValueError('Parâmetros de fluência devem ser números finitos.')
        if self.A_pa_n_s<=0 or self.n<=0 or self.Q_j_mol<0 or not -273.15<self.temperature_range_c[0]<=self.temperature_range_c[1] or not 0<=self.stress_range_pa[0]<self.stress_range_pa[1]:
            raise ValueError('Constantes ou faixas de fluência inválidas.')

    def rate(self,stress_pa,temperature_c):
        values=[self.A_pa_n_s,self.n,self.Q_j_mol,stress_pa,temperature_c,
                *self.temperature_range_c,*self.stress_range_pa]
        if not self.grade.strip() or not self.source.strip() or not all(math.isfinite(v) for v in values):
            raise ValueError('Fluência exige Steel Grade, fonte e parâmetros finitos.')
        if self.A_pa_n_s<=0 or self.n<=0 or self.Q_j_mol<0 or temperature_c<=-273.15:
            raise ValueError('Parâmetros constitutivos inválidos.')
        if not self.temperature_range_c[0]<=temperature_c<=self.temperature_range_c[1]:
            raise ValueError('Temperatura fora da calibração da fluência.')
        if not self.stress_range_pa[0]<=abs(stress_pa)<=self.stress_range_pa[1]:
            raise ValueError('Tensão fora da calibração da fluência.')
        if stress_pa==0:return 0.
        lograte=math.log(self.A_pa_n_s)+self.n*math.log(abs(stress_pa))-self.Q_j_mol/(8.314462618*(temperature_c+273.15))
        return math.copysign(math.exp(lograte),stress_pa)

    def constant_stress_strain(self,stress_pa,temperature_c,hours):
        if not math.isfinite(hours) or hours<0: raise ValueError('Tempo deve ser não negativo.')
        return self.rate(stress_pa,temperature_c)*hours*3600
