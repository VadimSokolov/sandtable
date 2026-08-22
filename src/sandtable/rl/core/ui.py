import numpy as np
import pygame
import math

def pygame_supervisory_loop(env, buffer=None, n_actions=7, n_agents=20):
    resp = input("\nPlay a REAL-TIME Pygame supervisory episode? [y/N]: ").strip().lower()
    if resp != 'y':
        return

    """ Allows human to play one episode using Pygame to set a high score and seed the MC search. """
    import pygame
    import math
    pygame.init()
    
    base_env = env.unwrapped
    size_x, size_y = base_env.scenario.size
    
    width, height = 800, 800
    screen = pygame.display.set_mode((width, height))
    pygame.display.set_caption("Sandtable Real-Time Play (MC Mode)")
    clock = pygame.time.Clock()
    
    def to_screen(x, y):
        sx = int((x / size_x) * width)
        sy = int((y / size_y) * height)
        sy = height - sy
        return sx, sy

    font = pygame.font.SysFont(None, 24)
    big_font = pygame.font.SysFont(None, 48)

    running = True
    print("\n--- Pygame Supervisory Mode ---")
    print("Currently in PAINT MODE (Paused).")
    print("- Left Click & Drag: Paint Positive Reward (+Brush)")
    print("- Right Click & Drag: Paint Negative Reward (-Brush)")
    print("- Middle Click & Drag: Erase Reward")
    print("- UP/DOWN Arrows: Adjust Brush Value")
    print("- SPACEBAR: Start PLAY MODE")
    print("- P: Pause (Back to Paint Mode)")
    print("- ESC: Exit")
    
    obs, _ = env.reset()
    done = False
    total_reward = 0
    step = 0
    human_actions = []
    
    
    last_action_id = 3 # Default RIGHT
    n_agents = base_env.max_agents
    
    mode = "PAINT"
    brush_value = 10.0
    
    while running and not done:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE and mode == "PAINT":
                    print("Starting PLAY MODE!")
                    mode = "PLAY"
                elif event.key == pygame.K_p and mode == "PLAY":
                    print("PAUSED (Back to Paint Mode)!")
                    mode = "PAINT"
                elif event.key == pygame.K_UP and mode == "PAINT":
                    brush_value += 1.0
                elif event.key == pygame.K_DOWN and mode == "PAINT":
                    brush_value = max(1.0, brush_value - 1.0)
        
        if not running:
            break
            
        screen.fill((30, 30, 30))
        
        # --- Paint Mode Logic ---
        if mode == "PAINT":
            buttons = pygame.mouse.get_pressed()
            mx, my = pygame.mouse.get_pos()
            
            # Map mouse to grid
            gx = int((mx / width) * env.grid_size[0])
            gy = int(((height - my) / height) * env.grid_size[1])
            gx = np.clip(gx, 0, env.grid_size[0]-1)
            gy = np.clip(gy, 0, env.grid_size[1]-1)
            
            if buttons[0]: # Left
                env.reward_grid[gx, gy] = brush_value
                env.initial_reward_grid[gx, gy] = brush_value
            elif buttons[2]: # Right
                env.reward_grid[gx, gy] = -brush_value
                env.initial_reward_grid[gx, gy] = -brush_value
            elif buttons[1]: # Middle
                env.reward_grid[gx, gy] = 0.0
                env.initial_reward_grid[gx, gy] = 0.0

            # Draw Custom Rewards Grid
            cw = width / env.grid_size[0]
            ch = height / env.grid_size[1]
            for i in range(env.grid_size[0]):
                for j in range(env.grid_size[1]):
                    val = env.reward_grid[i, j]
                    if val != 0:
                        # y is inverted
                        rect_x = i * cw
                        rect_y = height - (j + 1) * ch
                        color = (0, 100, 0) if val > 0 else (100, 0, 0)
                        pygame.draw.rect(screen, color, (rect_x, rect_y, cw, ch))
        
        # --- Play Mode Logic ---
        if mode == "PLAY":
            keys = pygame.key.get_pressed()
            
            act_id = last_action_id
            if keys[pygame.K_w] or keys[pygame.K_UP]: act_id = 0
            elif keys[pygame.K_s] or keys[pygame.K_DOWN]: act_id = 1
            elif keys[pygame.K_a] or keys[pygame.K_LEFT]: act_id = 2
            elif keys[pygame.K_d] or keys[pygame.K_RIGHT]: act_id = 3
            elif keys[pygame.K_c]: act_id = 4
            elif keys[pygame.K_e]: act_id = 5
            elif keys[pygame.K_v]: act_id = 6
                
            last_action_id = act_id
            actions = [act_id for _ in range(n_agents)]
            
            next_obs, reward, terminated, truncated, info = env.step(actions)
            done = terminated or truncated
            
            if buffer is not None:
                buffer.push(obs, actions, reward, next_obs, done)
            
            human_actions.append(actions)
            obs = next_obs
            
            total_reward += reward
            step += 1

        # --- Rendering (Both Modes) ---
        
        # Draw custom rewards in Play mode as well, but fainter
        if mode == "PLAY":
            surface = pygame.Surface((width, height), pygame.SRCALPHA)
            cw = width / env.grid_size[0]
            ch = height / env.grid_size[1]
            for i in range(env.grid_size[0]):
                for j in range(env.grid_size[1]):
                    val = env.reward_grid[i, j]
                    if val != 0:
                        rect_x = i * cw
                        rect_y = height - (j + 1) * ch
                        color = (0, 150, 0, 30) if val > 0 else (150, 0, 0, 30)
                        pygame.draw.rect(surface, color, (rect_x, rect_y, cw, ch))
            screen.blit(surface, (0,0))
            
        # Draw Goal
        goal_x, goal_y = base_env.scenario.objective.goal
        goal_radius = base_env.scenario.objective.goal_radius
        gx, gy = to_screen(goal_x, goal_y)
        gr_px = int((goal_radius / size_x) * width)
        pygame.draw.circle(screen, (0, 150, 0), (gx, gy), max(5, gr_px), 2)
        pygame.draw.circle(screen, (0, 255, 0), (gx, gy), 5)
        
        red_idx = np.where(base_env.red_mask)[0]
        blue_idx = np.where(base_env.blue_mask)[0]
        
        # Draw ranges
        if mode == "PLAY" and act_id == 4: # CUE
            surface = pygame.Surface((width, height), pygame.SRCALPHA)
            for i in blue_idx:
                if base_env.ent.alive[i]:
                    bx, by = to_screen(base_env.ent.x[i], base_env.ent.y[i])
                    sr_px = int((base_env.ent.sensor_range[i] * 1.5 / size_x) * width)
                    pygame.draw.circle(surface, (0, 0, 255, 50), (bx, by), sr_px)
            screen.blit(surface, (0,0))
            
        if mode == "PLAY" and act_id == 5: # ENGAGE
            for i in blue_idx:
                if base_env.ent.alive[i]:
                    bx, by = base_env.ent.x[i], base_env.ent.y[i]
                    bx_scr, by_scr = to_screen(bx, by)
                    wr = base_env.ent.weapon_range[i]
                    wr_px = int((wr / size_x) * width)
                    pygame.draw.circle(screen, (255, 0, 0), (bx_scr, by_scr), max(1, wr_px), 1)
                    
                    best_dist = wr
                    best_red = -1
                    for j in red_idx:
                        if base_env.ent.alive[j] and base_env.ent.seen[j]:
                            rx, ry = base_env.ent.x[j], base_env.ent.y[j]
                            d = math.hypot(bx - rx, by - ry)
                            if d <= best_dist:
                                best_dist = d
                                best_red = j
                    if best_red != -1:
                        rx, ry = base_env.ent.x[best_red], base_env.ent.y[best_red]
                        pygame.draw.line(screen, (255, 255, 0), to_screen(bx, by), to_screen(rx, ry), 2)
        
        # Red always engages Blue if in range and seen
        for j in red_idx:
            if base_env.ent.alive[j]:
                rx, ry = base_env.ent.x[j], base_env.ent.y[j]
                wr = base_env.ent.weapon_range[j]
                best_dist = wr
                best_blue = -1
                for i in blue_idx:
                    if base_env.ent.alive[i] and base_env.ent.seen[i]:
                        bx, by = base_env.ent.x[i], base_env.ent.y[i]
                        d = math.hypot(rx - bx, ry - by)
                        if d <= best_dist:
                            best_dist = d
                            best_blue = i
                if best_blue != -1:
                    bx, by = base_env.ent.x[best_blue], base_env.ent.y[best_blue]
                    pygame.draw.line(screen, (255, 100, 0), to_screen(rx, ry), to_screen(bx, by), 2)
        
        # Draw Entities
        for i in red_idx:
            if base_env.ent.alive[i]:
                rx, ry = to_screen(base_env.ent.x[i], base_env.ent.y[i])
                pygame.draw.circle(screen, (255, 50, 50), (rx, ry), 4)
                
        for i in blue_idx:
            if base_env.ent.alive[i]:
                bx, by = to_screen(base_env.ent.x[i], base_env.ent.y[i])
                pygame.draw.circle(screen, (50, 50, 255), (bx, by), 4)
                
        # Overlay Text
        if mode == "PAINT":
            msg = big_font.render(f"PAINT (Paused) | Brush: {brush_value} | SPACE to Play", True, (200, 200, 0))
            screen.blit(msg, (10, height - 50))
            inst = font.render("Use UP/DOWN arrows to change the brush value.", True, (150, 150, 150))
            screen.blit(inst, (10, height - 20))
        else:
            info_text = f"Step: {step} | Reward: {total_reward:.1f}"
            text_surf = font.render(info_text, True, (255, 255, 255))
            screen.blit(text_surf, (10, 10))
            act_text = ["UP", "DOWN", "LEFT", "RIGHT", "CUE", "ENGAGE", "EVADE"][act_id]
            cmd_surf = font.render(f"Command: {act_text}", True, (200, 200, 200))
            screen.blit(cmd_surf, (10, 35))
        
        if done and total_reward > 500:
            msg_surf = big_font.render("CONGRATULATIONS! Goal Reached!", True, (50, 255, 50))
            msg_rect = msg_surf.get_rect(center=(width//2, height//2))
            screen.blit(msg_surf, msg_rect)
        
        pygame.display.flip()
        
        if done and total_reward > 500:
            pygame.time.wait(2000)
            running = False
            
        clock.tick(30)
        
    pygame.quit()
    pygame.quit()
    if buffer is not None:
        print(f"Exited supervisory mode. Buffer size: {len(buffer)}")
    else:
        print("Exited supervisory mode.")
        
    trace = getattr(base_env, 'get_trace', lambda: None)()
    return total_reward, trace, step, human_actions
