"""Read-only street visibility telemetry; no additional random draws."""
import numpy as np
from unittest.mock import patch
from sandtable import behavior,sensing

class Observe:
    def __init__(self):self.bhv=None;self.k=0;self.total_pairs=0;self.blocked=0;self.first=None;self.seen_steps=0
    def __enter__(self):
        original_behavior,original_sensing=behavior.step,sensing.step
        def step(ent,bhv,*args,**kwargs):
            self.bhv=bhv
            bhv.study_urban_telemetry=dict(sensor_pairs=0,blocked_pairs=0,red_detected=0,first_red_detection=self.first)
            return original_behavior(ent,bhv,*args,**kwargs)
        def sense(ent,world,rng,comms=None):
            original_sensing(ent,world,rng,comms)
            distance=np.hypot(ent.x[:,None]-ent.x[None,:],ent.y[:,None]-ent.y[None,:])
            pairs=ent.alive[:,None]&ent.alive[None,:]&(ent.side[:,None]!=ent.side[None,:])&(distance<=ent.sensor_range[:,None])
            clear=world.los(ent.x[:,None],ent.y[:,None],ent.x[None,:],ent.y[None,:])
            blocked=int((pairs&~clear).sum());total=int(pairs.sum())
            seen=int((ent.seen&ent.alive&(ent.side==1)).sum())
            if seen and self.first is None:self.first=self.k+1
            self.total_pairs+=total;self.blocked+=blocked;self.seen_steps+=int(seen>0)
            self.bhv.study_urban_telemetry=dict(sensor_pairs=total,blocked_pairs=blocked,red_detected=seen,first_red_detection=self.first)
            self.k+=1
        self.bp=patch.object(behavior,'step',step);self.sp=patch.object(sensing,'step',sense)
        self.bp.__enter__();self.sp.__enter__();return self
    def __exit__(self,*args):self.sp.__exit__(*args);self.bp.__exit__(*args)
