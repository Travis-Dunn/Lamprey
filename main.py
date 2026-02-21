"""
Tank Gunner - Main
Entry point and game loop.

Requirements:
    pip install pygame numpy
"""
import sys
import pygame
from settings import *
from world import World
from renderer import Renderer
from audio import AudioManager


def main():
    pygame.init()
    pygame.mixer.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption(WINDOW_TITLE)
    clock = pygame.time.Clock()

    world = World()
    renderer = Renderer(screen)

    # ── Audio setup ──────────────────────────────────────
    audio = AudioManager()
    audio.register("traverse", "sounds/traverse.ogg",
                   loop=True, base_volume=AUDIO_TRAVERSE_VOL)
    # Future slots:
    # audio.register("fire",    "sounds/fire.ogg",    loop=False)
    # audio.register("hit",     "sounds/hit.ogg",     loop=False)
    # audio.register("ambient", "sounds/ambient.ogg", loop=True, base_volume=0.3)

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        dt = min(dt, 0.05)  # clamp to avoid spiral of death

        # ── Events ───────────────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    world.fire()
                    # audio.play_oneshot("fire")  # uncomment when asset exists

        # ── Update ───────────────────────────────────────
        keys = pygame.key.get_pressed()
        world.update(dt, keys)

        # ── Audio ────────────────────────────────────────
        audio.set_active("traverse", world.gun.is_traversing)
        audio.update(dt)

        # ── Draw ─────────────────────────────────────────
        renderer.draw(world)
        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()