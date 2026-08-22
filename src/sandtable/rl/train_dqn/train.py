import os
import sys
import time
import random
from collections import deque
import numpy as np

import torch
import torch.nn as nn
import torch.optim as optim

# Add the src folder to path to allow importing sandtable
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from sandtable.rl.env import SandtableEnv
from sandtable.rl.sandtable_mc_swarm import inject_trace_into_viewer, find_viewer_template
import webbrowser

from sandtable.rl.core.wrappers import CustomRewardGridWrapper
from sandtable.rl.core.models import QNetwork, ReplayBuffer
from sandtable.rl.core.ui import pygame_supervisory_loop

def train_dqn(scenario_path):
    print("Entered train_dqn function")
    print(f"Initializing Sandtable DQN Environment for {scenario_path}...")
    env = CustomRewardGridWrapper(SandtableEnv(scenario_path, seed=42), grid_size=(50, 50))
    print("Environment created")
    
    obs_dim = env.observation_space.shape[0]
    n_agents = env.max_agents
    n_actions = 7 # UP, DOWN, LEFT, RIGHT, CUE, ENGAGE, EVADE
    
    q_network = QNetwork(obs_dim, n_agents, n_actions)
    target_network = QNetwork(obs_dim, n_agents, n_actions)
    target_network.load_state_dict(q_network.state_dict())
    
    optimizer = optim.Adam(q_network.parameters(), lr=1e-3)
    loss_fn = nn.SmoothL1Loss()
    
    buffer = ReplayBuffer(capacity=50000)
    
    # Run interactive pre-training if requested
    pygame_supervisory_loop(env, buffer, n_actions, n_agents)
    
    # Hyperparameters
    num_episodes = 200
    batch_size = 64
    gamma = 0.99
    epsilon = 0.5 if len(buffer) >= batch_size else 1.0
    epsilon_min = 0.05
    epsilon_decay = 0.995
    target_update_freq = 10
    
    if len(buffer) >= batch_size:
        print(f"\n--- Pre-training DQN on Human Replay Buffer ({len(buffer)} transitions) ---")
        for i in range(1000):
            b_state, b_action, b_reward, b_next_state, b_done = buffer.sample(batch_size)
            
            b_state = torch.FloatTensor(b_state)
            b_action = torch.LongTensor(b_action)
            b_reward = torch.FloatTensor(b_reward).unsqueeze(1)
            b_next_state = torch.FloatTensor(b_next_state)
            b_done = torch.FloatTensor(b_done).unsqueeze(1)
            
            current_q = q_network(b_state)
            current_q_taken = current_q.gather(2, b_action.unsqueeze(2)).squeeze(2)
            
            with torch.no_grad():
                next_q = target_network(b_next_state)
                max_next_q = next_q.max(dim=2)[0]
            
            target_q = b_reward + gamma * max_next_q * (1 - b_done)
            loss = loss_fn(current_q_taken, target_q)
            
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            
            if (i+1) % 200 == 0:
                print(f"Pre-training step {i+1}/1000 - Loss: {loss.item():.4f}")
                
        target_network.load_state_dict(q_network.state_dict())
        print("Pre-training complete! The AI has digested your gameplay.")
    
    best_reward = -float('inf')
    best_trace = None
    
    for episode in range(num_episodes):
        obs, _ = env.reset()
        done = False
        total_reward = 0
        step = 0
        
        while not done:
            # Epsilon-greedy action selection
            if random.random() < epsilon:
                # Random action for each agent
                actions = [random.randint(0, n_actions - 1) for _ in range(n_agents)]
            else:
                with torch.no_grad():
                    state_t = torch.FloatTensor(obs).unsqueeze(0)
                    q_vals = q_network(state_t) # shape: (1, n_agents, n_actions)
                    actions = q_vals.argmax(dim=2).squeeze(0).numpy().tolist()
            
            next_obs, reward, terminated, truncated, info = env.step(actions)
            done = terminated or truncated
            
            buffer.push(obs, actions, reward, next_obs, done)
            
            obs = next_obs
            total_reward += reward
            step += 1
            
            # Train step
            if len(buffer) >= batch_size:
                b_state, b_action, b_reward, b_next_state, b_done = buffer.sample(batch_size)
                
                b_state = torch.FloatTensor(b_state)
                b_action = torch.LongTensor(b_action)
                b_reward = torch.FloatTensor(b_reward).unsqueeze(1) # shape: (batch, 1)
                b_next_state = torch.FloatTensor(b_next_state)
                b_done = torch.FloatTensor(b_done).unsqueeze(1) # shape: (batch, 1)
                
                # Q-values for current state
                current_q = q_network(b_state) # shape: (batch, n_agents, n_actions)
                # Gather Q-values for the actions taken
                current_q_taken = current_q.gather(2, b_action.unsqueeze(2)).squeeze(2) # shape: (batch, n_agents)
                
                # Next Q-values from target network
                with torch.no_grad():
                    next_q = target_network(b_next_state) # shape: (batch, n_agents, n_actions)
                    max_next_q = next_q.max(dim=2)[0] # shape: (batch, n_agents)
                
                # Target Q value
                # We distribute the global reward to all agents equally
                target_q = b_reward + gamma * max_next_q * (1 - b_done)
                
                loss = loss_fn(current_q_taken, target_q)
                
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                
        epsilon = max(epsilon_min, epsilon * epsilon_decay)
        
        if episode % target_update_freq == 0:
            target_network.load_state_dict(q_network.state_dict())
            
        print(f"Episode {episode + 1}/{num_episodes}: Total Reward = {total_reward:.2f} (Steps: {step}, Epsilon: {epsilon:.2f})")
        
        if total_reward > best_reward:
            best_reward = total_reward
            best_trace = env.get_trace()
            best_trace["group"] = "RL DQN Agent"
            best_trace["label"] = f"DQN Best (Reward: {best_reward:.2f})"
            best_trace["seed"] = 42
            
            # Save model
            torch.save(q_network.state_dict(), "best_dqn_model.pth")

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
    # Choose a scenario to run
    scenario_file = "scenarios/uc3_route_defilade.json"
    scenario_full_path = os.path.join(os.path.dirname(__file__), "../../..", scenario_file)
    
    if not os.path.exists(scenario_full_path):
        # Fallback if path is wrong
        scenario_full_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../scenarios/uc3_route_defilade.json"))
        
    print(scenario_full_path)
    train_dqn(scenario_full_path)
