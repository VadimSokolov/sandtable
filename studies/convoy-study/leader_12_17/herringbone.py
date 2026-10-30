"""Experimental straight-road geometry adapter, NOT a production sandtable feature.

Uses existing contact detection/release with action=halt. During contact,
the planner sends vehicles to alternating side stations. Motion uses the engine's
normal finite speed and turn limits; only parked orientation is prescribed.
20 m offsets and the parking rule are teaching assumptions, not calibration.
No obstacle avoidance, fire-sector bonus, dismounts, or collision guarantees.
"""
from contextlib import ExitStack
from unittest.mock import patch
import numpy as np
from sandtable import planning, motion


class Herringbone:
    def __init__(self, offset=20.):
        self.offset = float(offset)
        self.active = False
        self.anchors = None
        self.entry = None
        self.ids = None
        self.ent = None
        self.bhv = None
        self.episodes = 0
        self.parked_vehicle_steps = 0
        self.maneuver_vehicle_steps = 0
        self.park_checks = 0
        self.route = None
        self.park_heading = None

    def __enter__(self):
        self.stack = ExitStack()
        original_plan, original_motion = planning.step, motion.step
        def plan(ent, world, scn, *args, **kwargs):
            boxes=getattr(world,'building_boxes',None)
            if boxes is not None and np.size(boxes):
                raise ValueError('Teaching Herringbone does not support building obstacles')
            self.route=getattr(world,'route',None)
            original_plan(ent, world, scn, *args, **kwargs)
            if self.ids is None:
                self.ids=np.flatnonzero((ent.side==0)&(ent.domain==0)&ent.alive)
            bhv=kwargs.get('bhv')
            self.ent,self.bhv=ent,bhv
            contact=bhv is not None and bhv.in_contact
            if contact and not self.active:
                self.ids=np.flatnonzero((ent.side==0)&(ent.domain==0)&ent.alive)
                self.entry=np.column_stack((ent.x.copy(),ent.y.copy()))
                self.anchors=self.entry.copy()
                self.sign=np.ones(ent.n)
                self.sign[self.ids[1::2]]=-1
                self.anchors[self.ids,0]+=self.offset
                self.anchors[self.ids,1]+=self.sign[self.ids]*self.offset
                self.park_heading=self.sign*np.pi/4
                if self.route is not None:
                    s,_=self.route.project(ent.x[self.ids],ent.y[self.ids])
                    rx,ry,rh=self.route.point_at(s+self.offset)
                    self.anchors[self.ids,0]=rx-self.sign[self.ids]*self.offset*np.sin(rh)
                    self.anchors[self.ids,1]=ry+self.sign[self.ids]*self.offset*np.cos(rh)
                    self.park_heading[self.ids]=rh+self.sign[self.ids]*np.pi/4
                assert (self.anchors[self.ids,0] < world.size[0]).all()
                assert (self.anchors[self.ids,1] > 0).all() and (self.anchors[self.ids,1] < world.size[1]).all()
                self.episodes+=1
            self.active=bool(contact)
            if self.active:
                ids=self.ids[ent.alive[self.ids]]
                ent.tgt_x[ids]=self.anchors[ids,0]
                ent.tgt_y[ids]=self.anchors[ids,1]
            elif self.ids is not None:
                # A follower ahead of its station waits for the column to catch
                # up; it must not chase a station behind it around in circles.
                ids=self.ids[ent.alive[self.ids]]
                if self.route is None:
                    wait=ids[ent.tgt_x[ids] <= ent.x[ids]+.05]
                else:
                    s,cross=self.route.project(ent.x[ids],ent.y[ids])
                    target_s,_=self.route.project(ent.tgt_x[ids],ent.tgt_y[ids])
                    wait=ids[target_s<=s+.05]
                    # Rejoin perpendicular to the local route before proceeding.
                    returning=cross>.08
                    rx,ry,_=self.route.point_at(s[returning])
                    ent.tgt_x[ids[returning]]=rx;ent.tgt_y[ids[returning]]=ry
                    wait=wait[~np.isin(wait,ids[returning])]
                    for j,i in enumerate(ids):
                        if returning[j]:continue
                        next_vertices=self.route.cum_dist[self.route.cum_dist>s[j]+.05]
                        if len(next_vertices) and target_s[j]>next_vertices[0]:
                            rx,ry,_=self.route.point_at(next_vertices[0])
                            ent.tgt_x[i]=rx;ent.tgt_y[i]=ry
                ent.tgt_x[wait]=ent.x[wait]
                ent.tgt_y[wait]=ent.y[wait]
            bhv.study_herringbone_active=self.active
        def move(ent,*args,**kwargs):
            previous_heading=ent.heading.copy()
            # The base unicycle advances at cruise speed even when facing away
            # from a nearby station. That produces orbits during approach/rejoin.
            # Apply steering-aware arrival throughout this experimental arm,
            # including its initial formation and its return to the column.
            dt=args[1]  # world, dt, tempo
            saved_cap=ent.speed_cap.copy()
            if self.ids is not None:
                ids=self.ids[ent.alive[self.ids]]
                dx=ent.tgt_x[ids]-ent.x[ids]
                dy=ent.tgt_y[ids]-ent.y[ids]
                distance=np.hypot(dx,dy)
                desired=np.arctan2(dy,dx)
                error=(desired-previous_heading[ids]+np.pi)%(2*np.pi)-np.pi
                next_error=error-np.clip(error,-ent.turn_rate[ids]*dt,ent.turn_rate[ids]*dt)
                cap=np.minimum(ent.max_speed[ids]*np.maximum(0,np.cos(next_error)),distance/(2*dt))
                if self.route is not None:
                    # Align before translating on a polyline/rejoin leg. Otherwise
                    # each turn creates a new lateral error and rejoin can chatter.
                    cap=np.where(np.abs(next_error)>.001,0.,cap)
                # Latch the stop within tolerance; do not chase floating-point residue.
                if self.active:
                    cap=np.where(distance<.05,0.,cap)
                ent.speed_cap[ids]=np.minimum(saved_cap[ids],cap)
            try:
                original_motion(ent,*args,**kwargs)
            finally:
                ent.speed_cap[:]=saved_cap
            parked=np.zeros(ent.n,dtype=bool)
            if self.active:
                ids=self.ids[ent.alive[self.ids]]
                distances=np.hypot(ent.x[ids]-self.anchors[ids,0],ent.y[ids]-self.anchors[ids,1])
                at=ids[distances<.05]
                # Heading evolves through the existing turn-rate limit, even at rest.
                target=self.park_heading[at]
                delta=(target-previous_heading[at]+np.pi)%(2*np.pi)-np.pi
                ent.heading[at]=previous_heading[at]+np.clip(delta,-ent.turn_rate[at]*dt,ent.turn_rate[at]*dt)
                parked[at]=True
                self.parked_vehicle_steps+=len(at)
                self.maneuver_vehicle_steps+=len(ids)-len(at)
                if len(at):
                    assert np.allclose(ent.x[at],self.anchors[at,0],atol=.05)
                    assert np.allclose(ent.y[at],self.anchors[at,1],atol=.05)
                    self.park_checks+=1
            self.bhv.study_herringbone_parked=parked
        self.stack.enter_context(patch.object(planning,'step',plan))
        self.stack.enter_context(patch.object(motion,'step',move))
        return self

    def __exit__(self,*args):
        return self.stack.__exit__(*args)
