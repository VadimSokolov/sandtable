import numpy as np
import gym
from gym import spaces
from sandtable.scenario import Scenario, build_entities
from sandtable.world import build_world
from sandtable.seeding import make_rng
from sandtable import metrics, motion, sensing, engagement, belief, mechanics, c2, counter_uas
from sandtable.entities import BLUE, RED, GROUND, AIR
from sandtable.comms_ew import build_comms
from sandtable.replay import _downsample
import json
from pathlib import Path

class SandtableEnv(gym.Env):
    """
    OpenAI Gym-style environment for Sandtable.
    Actions:
      0: UP
      1: DOWN
      2: LEFT
      3: RIGHT
      4: CUE (sense/share picture)
      5: ENGAGE (shoot nearest)
      6: EVADE (move to nearest cover/jitter)
    """
    
    def __init__(self, scenario_path: str, seed: int = 42):
        super().__init__()
        self.scenario = Scenario.from_dict(json.loads(Path(scenario_path).read_text()))
        self.seed = seed
        self.rng = make_rng(seed, self.scenario.id)
        
        self.dt = self.scenario.dt
        self.tempo = float(self.scenario.params.get("tempo", 1.0))
        
        self.world = None
        self.ent = None
        self.blue_mask = None
        self.red_mask = None
        
        self.max_agents = 20
        # MultiDiscrete for N blue agents, 7 actions each
        self.action_space = spaces.MultiDiscrete([7] * self.max_agents)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(self.max_agents*3 + 20*3,), dtype=np.float32)
        
        # For viewer trace
        self.frames = []
        self.kill_buf = []

    def snapshot(self):
        if self.ent is None:
            return
        self.frames.append({
            "t": round(float(self.t), 1),
            "x": [round(float(v), 1) for v in self.ent.x],
            "y": [round(float(v), 1) for v in self.ent.y],
            "alive": [int(v) for v in self.ent.alive],
            "seen": [int(v) for v in self.ent.seen],
            "cq": [round(float(v), 2) for v in self.ent.control_quality] if hasattr(self.ent, "control_quality") else [1.0]*self.ent.n,
            "kills": [[s, tg] for s, tg in self.kill_buf],
        })
        self.kill_buf.clear()

    def reset(self, *, seed: int | None = None, options: dict | None = None) -> tuple[np.ndarray, dict]:
        super().reset(seed=seed)
        if seed is not None:
            self.seed = seed
        self.rng = make_rng(self.seed, self.scenario.id)
        self.world = build_world(self.scenario, self.rng)
        self.ent = build_entities(self.scenario, self.rng)
        
        self.mech = mechanics.build_mech(self.scenario)
        if self.mech is not None:
            mechanics.arm(self.ent, self.mech)
            
        self.comms = build_comms(self.scenario)
        self.op = c2.build_c2(self.scenario, self.ent)
        self.cuas = counter_uas.build_counter_uas(self.scenario, self.ent)
            
        self.blue_mask = self.ent.side == BLUE
        self.red_mask = self.ent.side == RED
        self.n_blue = int(self.blue_mask.sum())
        
        self.init_counts = {BLUE: int((self.ent.side == BLUE).sum()), RED: int((self.ent.side == RED).sum())}
        ground_blue0 = int(((self.ent.side == BLUE) & (self.ent.domain == GROUND)).sum())
        self.assault0 = ground_blue0 if ground_blue0 > 0 else self.init_counts[BLUE]
        self.need = self.scenario.objective.survive_fraction * self.assault0
        
        self.t = 0.0
        self.n_steps = max(int(self.scenario.duration / self.dt), 1)
        self.step_idx = 0
        
        self.frames = []
        self.kill_buf = []
        self.snapshot()
        
        return self._get_obs(), {}

    def _get_obs(self):
        obs = np.zeros(self.max_agents * 3 + 20 * 3, dtype=np.float32)
        if self.ent is None or self.blue_mask is None or self.red_mask is None:
            return obs
        blue_idx = np.where(self.blue_mask)[0]
        for i, idx in enumerate(blue_idx[:self.max_agents]):
            obs[i*3] = self.ent.x[idx]
            obs[i*3+1] = self.ent.y[idx]
            obs[i*3+2] = self.ent.hp[idx] if self.ent.alive[idx] else 0.0
            
        red_idx = np.where(self.red_mask)[0]
        offset = self.max_agents * 3
        for i, idx in enumerate(red_idx[:20]):
            obs[offset + i*3] = self.ent.x[idx]
            obs[offset + i*3+1] = self.ent.y[idx]
            obs[offset + i*3+2] = self.ent.hp[idx] if self.ent.alive[idx] else 0.0
            
        return obs

    def step(self, action):
        if self.ent is None or self.world is None or self.blue_mask is None or self.red_mask is None:
            return self._get_obs(), 0.0, True, False, {}
            
        blue_idx = np.where(self.blue_mask)[0]
        
        engage_mask = np.zeros_like(self.ent.alive, dtype=bool)
        cue_mask = np.zeros_like(self.ent.alive, dtype=bool)
        
        if self.op is not None:
            c2.step(self.ent, self.op, self.comms, self.scenario, self.step_idx, self.rng)
            
        for i, idx in enumerate(blue_idx):
            if not self.ent.alive[idx]:
                continue
                
            act = action[i] if i < len(action) else 0
            dist = self.ent.max_speed[idx] * self.dt
            
            if act == 0: # UP
                self.ent.tgt_y[idx] = self.ent.y[idx] + dist
                self.ent.tgt_x[idx] = self.ent.x[idx]
            elif act == 1: # DOWN
                self.ent.tgt_y[idx] = self.ent.y[idx] - dist
                self.ent.tgt_x[idx] = self.ent.x[idx]
            elif act == 2: # LEFT
                self.ent.tgt_x[idx] = self.ent.x[idx] - dist
                self.ent.tgt_y[idx] = self.ent.y[idx]
            elif act == 3: # RIGHT
                self.ent.tgt_x[idx] = self.ent.x[idx] + dist
                self.ent.tgt_y[idx] = self.ent.y[idx]
            elif act == 4: # CUE
                cue_mask[idx] = True
            elif act == 5: # ENGAGE
                engage_mask[idx] = True
            elif act == 6: # EVADE
                self.ent.tgt_x[idx] = self.ent.x[idx] + self.rng.uniform(-dist, dist)
                self.ent.tgt_y[idx] = self.ent.y[idx] + self.rng.uniform(-dist, dist)

        motion.step(self.ent, self.world, self.dt, self.tempo)
        
        orig_sensor_range = self.ent.sensor_range.copy()
        self.ent.sensor_range[cue_mask] *= 1.5 
        sensing.step(self.ent, self.world, self.rng, self.comms)
        self.ent.sensor_range = orig_sensor_range 
        
        if self.mech is not None:
            mechanics.decay(self.ent, self.mech)
            
        red_idx = np.where(self.red_mask)[0]
        engage_mask[red_idx] = True 
        
        orig_wpn_range = self.ent.weapon_range.copy()
        self.ent.weapon_range[~engage_mask] = 0.0
        engagement.step(self.ent, self.world, self.dt, self.rng, events=self.kill_buf, mech=self.mech)
        self.ent.weapon_range = orig_wpn_range
        
        if self.cuas is not None:
            counter_uas.step(self.ent, self.cuas, self.rng)

        self.t += self.dt
        self.step_idx += 1
        
        if self.step_idx % 10 == 0:
            self.snapshot()
        
        done = False
        reward = -0.1 
        
        reached = metrics.blue_at_goal(self.ent, self.scenario).sum()
        
        if reached >= self.need:
            done = True
            reward += 1000.0
            self.snapshot()
        elif self.step_idx >= self.n_steps:
            done = True
            reward -= 50.0
            self.snapshot()
            
        if not self.ent.alive[self.blue_mask].any():
            done = True
            reward -= 100.0
            self.snapshot()
            
        return self._get_obs(), reward, done, False, {}

    def get_trace(self):
        if self.ent is None or self.world is None:
            return {}
        result = metrics.compute(self.scenario, self.init_counts, self.ent, self.t if self.t > 0 else None, self.t, assault0=self.assault0)
        gx, gy = self.scenario.objective.goal
        return {
            "name": self.scenario.name,
            "size": [float(self.scenario.size[0]), float(self.scenario.size[1])],
            "dt": self.dt,
            "stride": 10,
            "params": {k: (round(v, 3) if isinstance(v, float) else v) for k, v in self.scenario.params.items()},
            "objective": {"goal": [float(gx), float(gy)], "radius": float(self.scenario.objective.goal_radius)},
            "terrain": {
                "cover": _downsample(self.world.cover),
                "conceal": _downsample(self.world.conceal),
            },
            "entities": [
                {
                    "side": int(self.ent.side[i]),
                    "domain": int(self.ent.domain[i]),
                    "sensor_range": float(self.ent.sensor_range[i]),
                    "weapon_range": float(self.ent.weapon_range[i]),
                }
                for i in range(self.ent.n)
            ],
            "frames": self.frames,
            "outcome": {
                "success": result["success"],
                "blue_losses": result["blue_losses"],
                "red_losses": result["red_losses"],
                "detection_coverage": 0.5, # Placeholder for now
                "mission_time": result["mission_time"],
            },
        }
