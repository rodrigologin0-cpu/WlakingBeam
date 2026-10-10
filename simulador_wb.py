"""Lançador Windows/Linux. O arquivo legado sem extensão permanece disponível."""
import argparse
from wb_physics.legacy import geometry


def main():
    parser=argparse.ArgumentParser(description='Walking Beam: geometria e sustentação termomecânica')
    parser.add_argument('--geometrico',action='store_true',help='Executa somente a interface geométrica anterior')
    args=parser.parse_args()
    geometry()['App'](enable_thermomechanical=not args.geometrico).run()

if __name__=='__main__':
    main()
