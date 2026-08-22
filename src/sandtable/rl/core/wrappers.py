import gym
import numpy as np

class CustomRewardGridWrapper(gym.Wrapper):
    def __init__(self, env, grid_size=(50, 50)):
        super().__init__(env)
        self.grid_size = grid_size
        self.reward_grid = np.zeros(grid_size)
        self.initial_reward_grid = np.zeros(grid_size)

    def reset(self, **kwargs):
        obs, info = self.env.reset(**kwargs)
        self.reward_grid = self.initial_reward_grid.copy()
        return obs, info

    def step(self, action):
        obs, reward, terminated, truncated, info = self.env.step(action)
        base_env = self.unwrapped
        size_x, size_y = base_env.scenario.size
        
        # Add custom cell rewards based on blue agent positions
        blue_idx = np.where(base_env.blue_mask)[0]
        cell_reward = 0
        visited_cells = set()
        for i in blue_idx:
            if base_env.ent.alive[i]:
                gx = int((base_env.ent.x[i] / size_x) * self.grid_size[0])
                gy = int((base_env.ent.y[i] / size_y) * self.grid_size[1])
                gx = np.clip(gx, 0, self.grid_size[0]-1)
                gy = np.clip(gy, 0, self.grid_size[1]-1)
                visited_cells.add((gx, gy))
                
        for gx, gy in visited_cells:
            val = self.reward_grid[gx, gy]
            cell_reward += val
            # Dynamic rewarding: flip positive rewards to -10 to prevent returning
            if val > 0:
                self.reward_grid[gx, gy] = -10.0
                
        reward += cell_reward
        return obs, reward, terminated, truncated, info
