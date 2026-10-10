"""Acesso às mesmas funções/coordenadas do projeto original, sem abrir janelas."""
from functools import lru_cache
from pathlib import Path
import runpy

@lru_cache(maxsize=1)
def geometry():
    return runpy.run_path(str(Path(__file__).resolve().parents[1] / 'simulador_wb'), run_name='wb_geometry')
