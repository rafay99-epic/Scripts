import pygame
import sys
import random

# Initialize Pygame
pygame.init()

# Set up display
width, height = 800, 600
screen = pygame.display.set_mode((width, height))
pygame.display.set_caption("Flappy Bird")

# Colors
white = (255, 255, 255)
black = (0, 0, 0)
red = (255, 0, 0)

# Bird
bird_width = 50
bird_height = 50
bird_x = width // 4
bird_y = height // 2 - bird_height // 2
bird_velocity = 0
gravity = 0.5
jump_force = 10

# Pipes
pipe_width = 80
pipe_height = 500
pipe_gap = 200
pipe_velocity = 5
pipes = []

# Score
score = 0
font = pygame.font.Font(None, 36)

def draw_bird(x, y):
    pygame.draw.rect(screen, white, [x, y, bird_width, bird_height])

def draw_pipe(x, gap_start, gap_height):
    pygame.draw.rect(screen, white, [x, 0, pipe_width, gap_start])
    pygame.draw.rect(screen, white, [x, gap_start + gap_height, pipe_width, height - gap_start - gap_height])

def draw_score(score):
    score_text = font.render("Score: " + str(score), True, white)
    screen.blit(score_text, [10, 10])

def game_over():
    font_large = pygame.font.Font(None, 72)
    game_over_text = font_large.render("Game Over", True, red)
    screen.blit(game_over_text, [width // 4, height // 2])
    pygame.display.flip()
    pygame.time.wait(2000)
    pygame.quit()
    sys.exit()

clock = pygame.time.Clock()

while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
            bird_velocity = -jump_force

    # Update bird position
    bird_velocity += gravity
    bird_y += bird_velocity

    # Spawn pipes
    if len(pipes) == 0 or pipes[-1]["x"] < width - width // 2:
        gap_start = random.randint(50, height - 50 - pipe_gap)
        pipes.append({"x": width, "gap_start": gap_start, "gap_height": pipe_gap})

    # Update pipe positions
    for pipe in pipes:
        pipe["x"] -= pipe_velocity

        # Check for collisions
        if bird_x < pipe["x"] + pipe_width and bird_x + bird_width > pipe["x"]:
            if bird_y < pipe["gap_start"] or bird_y + bird_height > pipe["gap_start"] + pipe["gap_height"]:
                game_over()

        # Check for passing pipes
        if pipe["x"] + pipe_width < bird_x:
            score += 1
            pipes.remove(pipe)

    # Clear the screen
    screen.fill(black)

    # Draw pipes
    for pipe in pipes:
        draw_pipe(pipe["x"], pipe["gap_start"], pipe["gap_height"])

    # Draw bird
    draw_bird(bird_x, bird_y)

    # Draw score
    draw_score(score)

    # Update display
    pygame.display.flip()

    # Cap the frame rate
    clock.tick(30)
