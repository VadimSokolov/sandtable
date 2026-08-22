import torch
import torch.nn as nn
import numpy as np
import random
from collections import deque

class QNetwork(nn.Module):
    def __init__(self, obs_dim, n_agents, n_actions):
        super(QNetwork, self).__init__()
        self.n_agents = n_agents
        self.n_actions = n_actions
        
        self.fc1 = nn.Linear(obs_dim, 256)
        self.relu1 = nn.ReLU()
        self.fc2 = nn.Linear(256, 256)
        self.relu2 = nn.ReLU()
        self.out = nn.Linear(256, n_agents * n_actions)
        
    def forward(self, x):
        x = self.relu1(self.fc1(x))
        x = self.relu2(self.fc2(x))
        q_vals = self.out(x)
        return q_vals.view(-1, self.n_agents, self.n_actions)

class ReplayBuffer:
    def __init__(self, capacity=100000):
        self.buffer = deque(maxlen=capacity)
    
    def push(self, state, action, reward, next_state, done):
        self.buffer.append((state, action, reward, next_state, done))
        
    def sample(self, batch_size):
        batch = random.sample(self.buffer, batch_size)
        state, action, reward, next_state, done = map(np.stack, zip(*batch))
        return state, action, reward, next_state, done
        
    def __len__(self):
        return len(self.buffer)
