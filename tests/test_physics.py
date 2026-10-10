"""Fixtures sintéticas: números para validar equações, não dados de Steel Grade."""
import unittest
from dataclasses import replace
from pathlib import Path
from copy import deepcopy
import numpy as np
from wb_physics.beam import Pad, solve_beam, UnsupportedEquilibrium
from wb_physics.materials import Material, MissingMaterial
from wb_physics.analysis import Case, evaluate, lift_sweep, drift_sweep, SCENARIOS, thermal_history, calculated_intervals
from wb_physics.creep import NortonParameters
from wb_physics.legacy import geometry

M=Material('FIXTURE SINTÉTICA — NÃO OPERACIONAL','Teste matemático, não ficha de aço',7800.,((20.,200e9),(1000.,80e9)),((20.,1e-5),(1000.,1e-5)))

class StructuralTests(unittest.TestCase):
    def assert_balance(self,r):
        self.assertLess(abs(r.force_error_n)/r.total_weight_n,1e-5)
        self.assertLess(abs(r.moment_error_nm)/(r.total_weight_n*r.x_m[-1]),1e-5)
        self.assertTrue(np.all(r.contact_reactions_n>=0))
        self.assertTrue(np.all(r.contact_gap_m>=-1e-7))
        self.assertLess(np.max(abs(r.contact_reactions_n*r.contact_gap_m)),r.total_weight_n*1e-7)

    def test_simply_supported_analytical(self):
        L,b,t,E,rho=4.,1.,.2,200e9,7800.
        r=solve_beam(L,b,t,E,rho,[Pad('left',0,0),Pad('right',L,0)],max_element_m=.1)
        q=rho*b*t*9.80665;I=b*t**3/12
        exact=5*q*L**4/(384*E*I)
        self.assertAlmostEqual(r.max_deflection_m/exact,1.,places=5)
        self.assertAlmostEqual(r.reactions_n['left']/(q*L),.5,places=6)
        self.assertLess(abs(r.stress_max_pa/(q*L**2/8*t/2/I)-1.),.001)  # curvatura FE convergente
        self.assert_balance(r)

    def test_lower_moving_is_gap_not_imposed_deflection(self):
        r=evaluate(Case(width_mm=1000,thickness_mm=200,temperature_c=1000),M)['beam']
        self.assertIsNotNone(r);self.assert_balance(r)
        self.assertAlmostEqual(sum(v for k,v in r.reactions_n.items() if k.startswith('M')),0.,places=5)
        self.assertLess(r.max_deflection_m,.020)

    def test_two_and_three_hours_same_elastic_not_creep(self):
        c=Case(width_mm=1000,thickness_mm=200,temperature_c=1000)
        rows=thermal_history(c,M,[{'hours':2,'mean_c':1000},{'hours':3,'mean_c':1000}])
        np.testing.assert_allclose(rows[0]['beam'].w_m,rows[1]['beam'].w_m)
        self.assertTrue(any('fluência' in n for n in rows[-1]['notes']))

    def test_moving_lift_recovers_and_transfers_load(self):
        c=Case(width_mm=1000,thickness_mm=200)
        rows=lift_sweep(c,M,[20,10,0,-10,-20])
        for row in rows:self.assert_balance(row['beam'])
        loads=[sum(v for k,v in r['beam'].reactions_n.items() if k.startswith('M')) for r in rows]
        self.assertEqual(loads[0],0)
        self.assertGreater(loads[-1],0)
        self.assertLess(sum(v for k,v in rows[-1]['beam'].reactions_n.items() if k.startswith('F')),rows[-1]['beam'].total_weight_n*.01)

    def test_lost_fixed_pad_has_no_reaction(self):
        c=Case(width_mm=1000,thickness_mm=200,disabled_fixed=(2,))
        r=evaluate(c,M)['beam']
        self.assertIsNotNone(r);self.assert_balance(r);self.assertEqual(r.reactions_n['F2'],0.)
        self.assertGreater(sum(v for k,v in r.reactions_n.items() if k.startswith('M')),0.)

    def test_no_load_from_outside_pad(self):
        r=solve_beam(4,1,.2,200e9,7800,[Pad('F1',.2,.1),Pad('F2',3.8,.1),Pad('outside',8,.1)])
        self.assertEqual(r.reactions_n['outside'],0.);self.assert_balance(r)

    def test_insufficient_support_is_reported(self):
        with self.assertRaises(UnsupportedEquilibrium):
            solve_beam(4,1,.2,200e9,7800,[Pad('offcentre',.2,.1)])
        r=solve_beam(4,1,.2,200e9,7800,[Pad('onepad',2,.2)])
        self.assertTrue(any('único pad' in w for w in r.warnings))

    def test_lengths_dimensions_temperatures_and_sections(self):
        for L in (4500,4560,4780,4860):
            for t in (200,225,250):
                for T in (20,1000):
                    for s in (1,2,3):
                        with self.subTest(L=L,t=t,T=T,s=s):
                            r=evaluate(Case(length_mm=L,width_mm=750,thickness_mm=t,temperature_c=T,section=s),M)['beam']
                            self.assertIsNotNone(r);self.assert_balance(r)

    def test_width_scaling_and_thickness(self):
        c=Case(width_mm=750,thickness_mm=200)
        a=evaluate(c,M)['beam'];b=evaluate(replace(c,width_mm=1950),M)['beam']
        self.assertAlmostEqual(a.max_deflection_m,b.max_deflection_m,places=9)
        self.assertAlmostEqual(b.total_weight_n/a.total_weight_n,1950/750)
        thicker=evaluate(replace(c,thickness_mm=250),M)['beam']
        self.assertLess(thicker.max_deflection_m,a.max_deflection_m)

    def test_drift_both_sides_all_alignments_and_lengths(self):
        for scenario in SCENARIOS:
            for mode in ('MIN','REF','MAX'):
                for L in (4500,4560,4780,4860):
                    rows=drift_sweep(Case(length_mm=L,width_mm=1000,thickness_mm=225,scenario=scenario,mode=mode),M,[-150,0,150])
                    for row in rows:
                        self.assertIsNotNone(row['beam']);self.assert_balance(row['beam'])
                    self.assertAlmostEqual(rows[0]['a_mm']-rows[-1]['a_mm'],300.)

    def test_mesh_refinement(self):
        c=Case(width_mm=1000,thickness_mm=200)
        a=evaluate(c,M,max_element_m=.15,pad_segments=2)['beam']
        b=evaluate(c,M,max_element_m=.075,pad_segments=4)['beam']
        self.assertLess(abs(a.max_deflection_m-b.max_deflection_m)/b.max_deflection_m,.02)
        self.assert_balance(a);self.assert_balance(b)

    def test_expansion_conserves_mass(self):
        c=Case(width_mm=1000,thickness_mm=200,temperature_c=1000)
        a=evaluate(c,M);b=evaluate(replace(c,expand=True),M)
        self.assertGreater(b['length_mm'],a['length_mm'])
        self.assertAlmostEqual(a['beam'].total_weight_n,b['beam'].total_weight_n,places=6)

class MaterialTests(unittest.TestCase):
    def test_no_material_geometry_only(self):
        r=evaluate(Case(width_mm=1000,thickness_mm=200),None)
        self.assertIsNone(r['beam']);self.assertIn('Somente',r['status'])
        self.assertIsNone(calculated_intervals([r]))

    def test_missing_dimensions(self):
        self.assertIsNone(evaluate(Case(),M)['beam'])

    def test_material_requires_source(self):
        with self.assertRaises(MissingMaterial):Material('Aço','',7800,((20,200e9),))
        with self.assertRaises(MissingMaterial):Material('Aço','Fonte',7800,())
        with self.assertRaises(MissingMaterial):Material('Aço','Fonte',7800,((20,0),))

    def test_no_extrapolation(self):
        with self.assertRaises(MissingMaterial):M.modulus(1100)
        with self.assertRaises(MissingMaterial):M.modulus(-20)
        with self.assertRaises(MissingMaterial):Material('G','S',7800,((20,200e9),)).modulus(21)

    def test_no_expansion_without_alpha(self):
        m=Material('G','S',7800,((20,200e9),(1000,80e9)))
        with self.assertRaises(MissingMaterial):evaluate(Case(width_mm=1000,thickness_mm=200,temperature_c=1000,expand=True),m)

    def test_history_validation(self):
        with self.assertRaises(ValueError):thermal_history(Case(),M,[{'hours':3,'mean_c':20},{'hours':2,'mean_c':20}])

    def test_norton_is_separate_traceable(self):
        n=NortonParameters('FIXTURE','Teste matemático — não aço',1e-30,3,0,(20,1000),(0,1e9))
        self.assertAlmostEqual(n.constant_stress_strain(1e6,500,2),7.2e-9,places=14)
        self.assertAlmostEqual(n.rate(-1e6,500),-n.rate(1e6,500))
        with self.assertRaises(ValueError):n.rate(1e6,1100)
        with self.assertRaises(ValueError):replace(n,source='').rate(1e6,500)

class RegressionTests(unittest.TestCase):
    def test_coordinates_and_original_json_preserved(self):
        g=geometry()
        self.assertEqual(g['FIXED'],{1:[940,3160,5500,6670,9010,11230],2:[1465,3685,6085,8485,10705],3:[940,3160,5500,6670,9010,11230]})
        self.assertEqual(g['MOVING'],{1:[1990,4330,7840,10180],2:[2515,4855,7315,9655],3:[1990,4330,7840,10180]})
        self.assertEqual(g['BASE']['13']['p'],591);self.assertEqual(g['BASE']['13']['q'],340)

    def test_alignment_proposed_endpoints_and_existing_triangle(self):
        from wb_physics.analysis import alignment
        c=Case(scenario='Proposta 790/520')
        self.assertEqual(alignment(replace(c,length_mm=4500))[0],790)
        self.assertEqual(alignment(replace(c,length_mm=4860))[0],520)
        ref,lo,hi=alignment(replace(c,length_mm=4679.5))[1]
        self.assertAlmostEqual(hi-ref,185);self.assertAlmostEqual(ref-lo,185)
        for family,f in geometry()['BASE'].items():
            lo0=deepcopy(f)
            ref,lo,hi=geometry()['alignment'](f,f['mid'],family)
            self.assertLessEqual(lo,ref);self.assertGreaterEqual(hi,ref);self.assertEqual(f,lo0)

    def test_legacy_a3_export(self):
        from matplotlib.figure import Figure
        from io import BytesIO
        g=geometry();f=deepcopy(g['BASE']['13']);f.update(p=720,q=490)
        d=g['model']('13',f,4560)
        fig=Figure(figsize=(420/25.4,297/25.4));g['draw'](fig,d)
        for fmt in ('pdf','svg','png'):
            stream=BytesIO();fig.savefig(stream,format=fmt);self.assertGreater(len(stream.getvalue()),1000)

if __name__=='__main__':unittest.main()
