import pygame
import sys

# 1. Initialize Pygame
pygame.init()

# Set up the display window (Width=800, Height=600)
width, height = 800, 600
screen = pygame.display.set_mode((width, height))
pygame.display.set_caption("My First Pygame!")

# Setup a clock to control the frame rate
clock = pygame.time.Clock()

# --- GAME VARIABLES ---
# The player's starting position
player_x = 400
player_y = 300
player_speed = 5
player_radius = 20

# 2. The Core Game Loop
running = True
while running:
    # --- A. PROCESS INPUT (Events) ---
    for event in pygame.event.get():
        # If the user clicks the 'X' button to close the window
        if event.type == pygame.QUIT:
            running = False

    # Check which keys are currently being pressed
    keys = pygame.key.get_pressed()

    if player_x < 0:
        player_x = 0
    if keys[pygame.K_s]:
        player_speed = 20
    else:
        player_speed = 5 
    
    # --- B. UPDATE STATE (Logic) ---
    if keys[pygame.K_LEFT]:
        player_x -= player_speed
    if keys[pygame.K_RIGHT]:
        player_x += player_speed
    if keys[pygame.K_UP]:
        player_y -= player_speed
    if keys[pygame.K_DOWN]:
        player_y += player_speed

    # Prevent the player from going off-screen (Optional challenge for you!)
    # if player_x < 0: player_x = 0
    
    # --- C. DRAW SCREEN (Visuals) ---
    # Fill the screen with a background color (RGB: Red, Green, Blue)
    screen.fill((30, 30, 40)) # Dark blueish-grey

    # Draw the player (A bright blue circle)
    pygame.draw.circle(screen, (255, 0, 0), (player_x, player_y), player_radius)
    
    # Update the display to show what we just drew
    pygame.display.flip()
    
    # Limit to 60 frames per second
    clock.tick(60)

# 3. Quit gracefully when the loop ends
pygame.quit()
sys.exit()
