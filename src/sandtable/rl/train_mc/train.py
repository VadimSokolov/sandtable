import numpy as np
import time
import os
import sys
import gym

# Add the src folder to path to allow importing sandtable
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sandtable.rl.env import SandtableEnv
from sandtable.rl.sandtable_mc_swarm import inject_trace_into_viewer, find_viewer_template
import webbrowser

from sandtable.rl.core.wrappers import CustomRewardGridWrapper
from sandtable.rl.core.ui import pygame_supervisory_loop as pygame_play_episode

def train_or_run(scenario_path):
    print(f"Initializing Sandtable RL Environment for {scenario_path}...")
    env = SandtableEnv(scenario_path, seed=42)
    # Apply custom reward grid wrapper
    env = CustomRewardGridWrapper(env, grid_size=(50, 50))
    
    num_episodes = 1000
    best_reward = -float('inf')
    best_trace = None
    human_actions = []
    
    result = pygame_play_episode(env)
    if result is not None and result[1] is not None:
        human_reward, human_trace, human_steps, human_actions = result
        print(f"Human episode finished. Reward: {human_reward:.2f} (Steps: {human_steps})")
        
        best_reward = human_reward
        best_trace = human_trace
        best_trace["group"] = "Human Player"
        best_trace["label"] = f"Human Best (Reward: {best_reward:.2f})"
        best_trace["seed"] = 42

    print("\nStarting Seeded Monte Carlo Search...")
    env.reset()
    n_blue = env.unwrapped.n_blue
    
    for episode in range(num_episodes):
        obs, _ = env.reset()
        done = False
        total_reward = 0
        step = 0
        
        while not done:
            # Seeded MC: 80% follow human trace, 20% random mutation
            if human_actions and step < len(human_actions):
                if np.random.rand() < 0.8:
                    actions = human_actions[step]
                else:
                    # Random mutation
                    actions = [np.random.randint(0, 7) for _ in range(n_blue)]
            else:
                # Random fallback if human trace is exhausted
                actions = [np.random.randint(0, 7) for _ in range(n_blue)]
            
            obs, reward, terminated, truncated, info = env.step(actions)
            done = terminated or truncated
            total_reward += reward
            step += 1
            
        print(f"Episode {episode + 1}: Total Reward = {total_reward:.2f} (Steps: {step})")
        
        if total_reward > best_reward:
            best_reward = total_reward
            best_trace = env.unwrapped.get_trace()
            best_trace["group"] = "RL Agent"
            best_trace["label"] = f"Seeded MC Best (Reward: {best_reward:.2f})"
            best_trace["seed"] = 42

    print(f"\nBest Reward: {best_reward:.2f}")
    
    if best_trace is not None:
        print("Generating viewer output for the best episode...")
        viewer_template = find_viewer_template()
        viewer_file = inject_trace_into_viewer(best_trace, viewer_template=viewer_template)
        
        print(f"Opening viewer at {viewer_file}")
        webbrowser.open(f"file://{viewer_file}")
    else:
        print("No successful episodes found. Skipping viewer generation.")

if __name__ == "__main__":
    scenario_file = "scenarios/uc3_route_defilade.json"
    scenario_full_path = os.path.join(os.path.dirname(__file__), "../../..", scenario_file)
    
    if not os.path.exists(scenario_full_path):
        scenario_full_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../scenarios/uc3_route_defilade.json"))
        
    print(scenario_full_path)
    train_or_run(scenario_full_path)
