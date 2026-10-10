"""Dados fornecidos pelo usuário. SI; temperatura em °C; sem extrapolação."""
from dataclasses import dataclass
import math
import numpy as np

class MissingMaterial(ValueError):
    pass

@dataclass(frozen=True)
class Material:
    grade: str
    source: str
    density_kg_m3: float
    elastic_table: tuple  # pares (temperatura °C, E Pa)
    expansion_table: tuple = ()  # pares (temperatura °C, alpha 1/K)

    def __post_init__(self):
        if not isinstance(self.grade,str) or not isinstance(self.source,str) or not self.grade.strip() or not self.source.strip():
            raise MissingMaterial('Informe Steel Grade e origem dos dados; não há aço padrão.')
        if not math.isfinite(self.density_kg_m3) or self.density_kg_m3 <= 0:
            raise MissingMaterial('Densidade positiva é obrigatória.')
        for name, table, positive in [('E(T)', self.elastic_table, True), ('alpha(T)', self.expansion_table, False)]:
            if not table and positive:
                raise MissingMaterial('Informe ao menos um valor rastreável de E(T).')
            xs = [p[0] for p in table]
            if xs != sorted(set(xs)) or any(not math.isfinite(v) for p in table for v in p):
                raise MissingMaterial(f'{name}: pontos devem ser finitos, únicos e ordenados.')
            if any(p[1] <= 0 if positive else p[1] < 0 for p in table):
                raise MissingMaterial(f'{name}: propriedades inválidas.')

    @staticmethod
    def interpolate(table, temperature, name):
        if not math.isfinite(temperature) or not table or not table[0][0] <= temperature <= table[-1][0]:
            raise MissingMaterial(f'{name}: temperatura {temperature:g} °C fora dos dados disponíveis; sem extrapolação.')
        return float(np.interp(temperature, [p[0] for p in table], [p[1] for p in table]))

    def modulus(self, temperature):
        return self.interpolate(self.elastic_table, temperature, 'E(T)')

    def expansion(self, initial, final):
        if initial == final:
            return 0.0
        self.interpolate(self.expansion_table, initial, 'alpha(T)')
        self.interpolate(self.expansion_table, final, 'alpha(T)')
        lo, hi = sorted([initial, final])
        points = [lo] + [p[0] for p in self.expansion_table if lo < p[0] < hi] + [hi]
        alpha = [self.interpolate(self.expansion_table, t, 'alpha(T)') for t in points]
        integral = sum((b-a)*(x+y)/2 for a,b,x,y in zip(points,points[1:],alpha,alpha[1:]))
        return integral if final >= initial else -integral

    @classmethod
    def from_dict(cls, data):
        return cls(data['grade'], data['source'], float(data['density_kg_m3']),
                   tuple(tuple(map(float,p)) for p in data['elastic_table']),
                   tuple(tuple(map(float,p)) for p in data.get('expansion_table', [])))
