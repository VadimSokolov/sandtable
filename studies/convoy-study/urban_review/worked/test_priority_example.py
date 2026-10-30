"""Small #18 selector diagnostic for the worked-test learning panel."""
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace
import numpy as np
from sandtable.entities import Entities, BLUE, RED


def test_control_priority_and_ineligible_fallback():
    path=Path(__file__).resolve().parents[2]/'red_priority_18/branch_sources/target_priority.py'
    spec=importlib.util.spec_from_file_location('worked_target_priority',path)
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
    ent=Entities.allocate(3)
    ent.side[:]=[BLUE,BLUE,RED];ent.convoy_role[:]=[0,1,-1]
    ent.x[:]=[100,40,0];ent.y[:]=0
    scn=SimpleNamespace(params={'target_priority':{'order':['control']}},objective=SimpleNamespace(goal=(200,0)))
    prio=module.build_target_priority(scn,ent)
    distance=np.abs(ent.x[:,None]-ent.x[None,:])
    eligible=np.zeros((3,3),bool);eligible[2,:2]=True
    target,_=module.select(ent,prio,eligible,distance,np.array([2]),np.array([1]))
    assert target.tolist()==[0]  # control at 100 m, despite cargo being nearer at 40 m
    eligible[2,0]=False
    target,_=module.select(ent,prio,eligible,distance,np.array([2]),np.array([1]))
    assert target.tolist()==[1]  # priority never restores an ineligible target
