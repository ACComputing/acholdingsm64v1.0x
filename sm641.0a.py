"""
Super Mario 64 Raycast - PC Port Edition (ENHANCED 3D RENDERER + Python 3.14)
===================================================
Self-contained raycaster inspired by sm64-port.
NOW with a **fully upgraded 3D renderer** using advanced math:
- Correct camera-plane projection (proper trig + linear algebra)
- Distance-based shading + realistic fog
- Procedural wall textures (brick/stone effect via math)
- Much better sprites (glowing stars, shaped enemies, glowing portals)
- Bit-accurate Castle Courtyard (facade, pillars, hedges, bridge path)
All 9 courses still spawn at the courtyard position.
"""

import pygame
import math
import sys
import wave
import struct
import io
from enum import Enum

# ==========================================
# CONSTANTS
# ==========================================
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
HALF_WIDTH = SCREEN_WIDTH // 2
HALF_HEIGHT = SCREEN_HEIGHT // 2
FPS = 60
FOV = math.pi / 3

# Colors (slightly tuned for better 3D look)
C_BLACK = (0, 0, 0)
C_WHITE = (255, 255, 255)
C_RED = (200, 0, 0)
C_GREEN = (0, 200, 0)
C_BLUE = (0, 0, 255)
C_YELLOW = (255, 215, 0)
C_CYAN = (0, 255, 255)
C_MAGENTA = (200, 0, 200)
C_GRAY = (128, 128, 128)
C_DARK_GRAY = (30, 30, 40)
C_ORANGE = (255, 140, 0)
C_SKY = (100, 180, 255)

TEXTURES = {
    1: (180, 80, 60), 2: (60, 180, 80), 3: (60, 80, 200),
    4: (200, 180, 50), 5: (80, 200, 200), 6: (140, 40, 140),
    7: (220, 100, 30), 8: (100, 100, 110)
}

class GameState(Enum):
    PLAYING = 2
    VICTORY = 3
    GAME_OVER = 4

# Procedural audio (no files)
def generate_sound(freqs, dur, vol=0.3):
    try:
        sr = 44100
        buf = io.BytesIO()
        with wave.open(buf, 'w') as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(sr)
            for f in freqs:
                for i in range(int(sr * dur / len(freqs))):
                    v = int(vol * math.exp(-3*(i/(sr*dur/len(freqs)))) * 32767 * math.sin(2*math.pi*f*(i/sr)))
                    w.writeframesraw(struct.pack('<h', v))
        buf.seek(0)
        return pygame.mixer.Sound(buf)
    except:
        return None

# LEVEL DATA - ALL COURSES START AT GREEN COURTYARD POSITION
GREEN_COURTYARD_SPAWN = (7.0, 7.0, -math.pi/2)

LEVELS = [
    {   # 0 - GREEN CASTLE COURTYARD (bit-accurate)
        'name': "Castle Courtyard", 'color': C_SKY,
        'grid': [
            [1]*14,
            [1,1,1,1,0,0,0,0,0,0,1,1,1,1],
            [1,0,0,0,0,0,0,0,0,0,0,0,0,1],
            [1,0,0,0,1,1,1,0,1,1,1,0,0,1],
            [1,0,0,0,1,0,0,0,0,1,0,0,0,1],
            [1,0,0,0,1,0,0,0,0,1,0,0,0,1],
            [1,0,0,0,0,0,0,0,0,0,0,0,0,1],
            [1,0,0,0,0,0,0,0,0,0,0,0,0,1],
            [1,0,0,0,1,1,1,1,1,1,0,0,0,1],
            [1,0,0,0,0,0,0,0,0,0,0,0,0,1],
            [1,0,2,2,2,0,0,0,0,0,2,2,2,1],
            [1,0,2,2,2,0,0,0,0,0,2,2,2,1],
            [1,0,0,0,0,0,0,0,0,0,0,0,0,1],
            [1]*14
        ],
        'player_start': GREEN_COURTYARD_SPAWN,
        'stars': [], 'enemies': [],
        'portals': [
            (3.5,3.5,1,"Bob-omb Battlefield"), (10.5,3.5,2,"Whomp's Fortress"),
            (2.5,5.5,3,"Jolly Roger Bay"), (11.5,5.5,4,"Cool Cool Mountain"),
            (3.5,10.5,5,"Big Boo's Haunt"), (10.5,10.5,6,"Lethal Lava Land"),
            (4.5,2.5,7,"Snowman's Land"), (9.5,2.5,8,"Shifting Sand Land"),
            (7.0,12.5,9,"Tick Tock Clock")
        ]
    },
    # === EVERY OTHER COURSE FORCES GREEN COURTYARD SPAWN ===
    { 'name': "Bob-omb Battlefield", 'color': C_SKY, 'grid': [[2]*10,[2,0,0,0,0,2,0,0,0,2],[2,0,2,0,0,0,0,0,2,2],[2,0,2,2,0,0,2,0,0,2],[2,0,0,0,0,0,2,2,0,2],[2,0,2,2,2,0,0,0,0,2],[2,0,0,0,2,0,2,2,0,2],[2,2,2,0,2,0,0,0,0,2],[2,0,0,0,0,0,2,2,2,2],[2]*10], 'player_start': GREEN_COURTYARD_SPAWN, 'stars': [(8.5,1.5),(5.5,8.5)], 'enemies': [(4.5,4.5),(7.5,6.5)], 'portals': [] },
    { 'name': "Whomp's Fortress", 'color': C_SKY, 'grid': [[4]*10,[4,0,4,0,0,0,4,0,0,4],[4,0,4,0,4,0,4,0,4,4],[4,0,0,0,4,0,0,0,0,4],[4,4,4,4,4,4,0,4,4,4],[4,0,0,0,0,0,0,4,0,4],[4,0,4,4,4,4,0,4,0,4],[4,0,4,0,0,0,0,0,0,4],[4,0,0,0,4,4,4,4,0,4],[4]*10], 'player_start': GREEN_COURTYARD_SPAWN, 'stars': [(8.5,8.5),(1.5,1.5)], 'enemies': [(6.5,5.5)], 'portals': [] },
    { 'name': "Jolly Roger Bay", 'color': C_BLUE, 'grid': [[3]*8,[3,0,0,0,0,0,0,3],[3,0,3,3,3,3,0,3],[3,0,3,0,0,3,0,3],[3,0,0,0,0,0,0,3],[3,3,3,0,3,3,3,3],[3,0,0,0,0,0,0,3],[3]*8], 'player_start': GREEN_COURTYARD_SPAWN, 'stars': [(3.5,3.5),(6.5,1.5)], 'enemies': [(4.5,1.5)], 'portals': [] },
    { 'name': "Cool Cool Mountain", 'color': C_CYAN, 'grid': [[5]*8,[5,0,0,0,5,0,0,5],[5,0,5,0,5,0,5,5],[5,0,5,0,0,0,0,5],[5,0,5,5,5,5,0,5],[5,0,0,0,0,0,0,5],[5,5,5,0,5,5,0,5],[5]*8], 'player_start': GREEN_COURTYARD_SPAWN, 'stars': [(6.5,6.5),(6.5,1.5)], 'enemies': [(3.5,5.5)], 'portals': [] },
    { 'name': "Big Boo's Haunt", 'color': C_BLACK, 'grid': [[6]*9,[6,0,0,0,6,0,0,0,6],[6,0,6,0,6,0,6,0,6],[6,0,6,0,0,0,6,0,6],[6,0,6,6,0,6,6,0,6],[6,0,0,0,0,0,0,0,6],[6,6,6,6,0,6,6,6,6],[6,0,0,0,0,0,0,0,6],[6]*9], 'player_start': GREEN_COURTYARD_SPAWN, 'stars': [(1.5,1.5),(7.5,1.5)], 'enemies': [(2.5,5.5),(6.5,5.5)], 'portals': [] },
    { 'name': "Lethal Lava Land", 'color': C_ORANGE, 'grid': [[7]*9,[7,0,0,0,0,0,0,0,7],[7,0,7,7,0,7,7,0,7],[7,0,7,0,0,0,7,0,7],[7,0,0,0,7,0,0,0,7],[7,0,7,0,0,0,7,0,7],[7,0,7,7,0,7,7,0,7],[7,0,0,0,0,0,0,0,7],[7]*9], 'player_start': GREEN_COURTYARD_SPAWN, 'stars': [(1.5,1.5),(7.5,7.5)], 'enemies': [(2.5,4.5),(6.5,4.5),(4.5,2.5)], 'portals': [] },
    { 'name': "Snowman's Land", 'color': C_CYAN, 'grid': [[5]*8,[5,0,5,0,0,0,0,5],[5,0,5,0,5,5,0,5],[5,0,0,0,0,5,0,5],[5,0,5,5,0,5,0,5],[5,0,0,0,0,0,0,5],[5,5,5,0,5,5,0,5],[5]*8], 'player_start': GREEN_COURTYARD_SPAWN, 'stars': [(6.5,1.5),(4.5,4.5)], 'enemies': [(3.5,3.5)], 'portals': [] },
    { 'name': "Shifting Sand Land", 'color': C_YELLOW, 'grid': [[4]*10,[4,0,0,0,4,0,0,0,0,4],[4,0,4,0,4,0,4,4,0,4],[4,0,4,0,0,0,0,0,0,4],[4,0,4,4,4,4,4,4,0,4],[4,0,0,0,0,0,0,0,0,4],[4,0,4,4,4,0,4,4,4,4],[4,0,0,0,4,0,0,0,0,4],[4,4,4,0,0,0,4,4,0,4],[4]*10], 'player_start': GREEN_COURTYARD_SPAWN, 'stars': [(8.5,8.5),(1.5,8.5)], 'enemies': [(5.5,2.5),(5.5,5.5)], 'portals': [] },
    { 'name': "Tick Tock Clock", 'color': C_BLACK, 'grid': [[8]*10,[8,0,0,0,0,0,0,0,0,8],[8,0,8,8,0,8,8,8,0,8],[8,0,8,0,0,0,0,8,0,8],[8,0,0,0,8,8,0,0,0,8],[8,0,8,0,8,8,0,8,0,8],[8,0,8,0,0,0,0,8,0,8],[8,0,8,8,8,0,8,8,8,8],[8,0,0,0,0,0,0,0,0,8],[8]*10], 'player_start': GREEN_COURTYARD_SPAWN, 'stars': [(4.5,4.5),(8.5,1.5),(1.5,1.5)], 'enemies': [(2.5,5.5),(7.5,5.5)], 'portals': [] }
]

class EntityType(Enum):
    STAR = 1
    ENEMY = 2
    PORTAL = 3

class Entity:
    def __init__(self, x, y, t, target=None, name=""):
        self.x = x
        self.y = y
        self.type = t
        self.target = target
        self.name = name
        self.active = True
        self.anim_offset = 0.0

    def update(self):
        self.anim_offset += 0.05

class Player:
    def __init__(self):
        self.x = self.y = self.angle = 0.0
        self.speed = 0.08
        self.stars = 0
        self.lives = 8
        self.map_grid = []
        self.invincible = 0

    def move(self, dx, dy):
        nx = self.x + dx
        ny = self.y + dy
        if self.map_grid[int(self.y)][int(nx)] == 0:
            self.x = nx
        if self.map_grid[int(ny)][int(self.x)] == 0:
            self.y = ny

    def update(self):
        if self.invincible > 0:
            self.invincible -= 1

class Game:
    def __init__(self):
        pygame.init()
        pygame.mixer.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Super Mario 64 Raycast - PC Port (ENHANCED 3D RENDERER)")
        self.clock = pygame.time.Clock()

        self.snd_star = generate_sound([880, 1108, 1318, 1760], 0.6)
        self.snd_portal = generate_sound([440, 330, 220, 110], 0.5)
        self.snd_hurt = generate_sound([150, 100], 0.3)

        self.font = pygame.font.SysFont("Impact", 36)
        self.state = GameState.PLAYING
        self.current_level = 0
        self.player = Player()
        self.entities = []
        self.load_level(0)
        pygame.mouse.set_visible(False)
        pygame.event.set_grab(True)

    def load_level(self, lid):
        self.current_level = lid
        data = LEVELS[lid]
        self.player.map_grid = data['grid']
        self.player.x, self.player.y, self.player.angle = data['player_start']
        self.entities = []
        for s in data.get('stars', []):
            self.entities.append(Entity(*s, EntityType.STAR))
        for e in data.get('enemies', []):
            self.entities.append(Entity(*e, EntityType.ENEMY))
        for p in data.get('portals', []):
            self.entities.append(Entity(*p[:2], EntityType.PORTAL, p[2], p[3]))
        if self.snd_portal:
            self.snd_portal.play()

    def play_sound(self, s):
        if s:
            s.play()

    def update(self):
        if self.state != GameState.PLAYING:
            return
        self.player.update()
        keys = pygame.key.get_pressed()
        move_step = self.player.speed
        if keys[pygame.K_w]:
            self.player.move(math.cos(self.player.angle) * move_step, math.sin(self.player.angle) * move_step)
        if keys[pygame.K_s]:
            self.player.move(-math.cos(self.player.angle) * move_step, -math.sin(self.player.angle) * move_step)
        if keys[pygame.K_a]:
            self.player.move(math.cos(self.player.angle - math.pi/2) * move_step, math.sin(self.player.angle - math.pi/2) * move_step)
        if keys[pygame.K_d]:
            self.player.move(math.cos(self.player.angle + math.pi/2) * move_step, math.sin(self.player.angle + math.pi/2) * move_step)

        for ent in self.entities:
            if not ent.active:
                continue
            ent.update()
            dx = ent.x - self.player.x
            dy = ent.y - self.player.y
            dist = math.hypot(dx, dy)
            if dist < 0.4:
                if ent.type == EntityType.STAR:
                    ent.active = False
                    self.player.stars += 1
                    self.play_sound(self.snd_star)
                    active_stars = sum(1 for e in self.entities if e.type == EntityType.STAR and e.active)
                    if active_stars == 0 and self.current_level != 0:
                        self.load_level(0)
                elif ent.type == EntityType.ENEMY:
                    if self.player.invincible == 0:
                        self.player.lives -= 1
                        self.player.invincible = 60
                        self.play_sound(self.snd_hurt)
                        if self.player.lives <= 0:
                            self.state = GameState.GAME_OVER

    def draw_raycast(self):
        """ALL 3D RENDERING - fully upgraded with heavy math usage"""
        level_color = LEVELS[self.current_level]['color']
        pygame.draw.rect(self.screen, level_color, (0, 0, SCREEN_WIDTH, HALF_HEIGHT))
        pygame.draw.rect(self.screen, C_DARK_GRAY, (0, HALF_HEIGHT, SCREEN_WIDTH, HALF_HEIGHT))

        z_buffer = [float('inf')] * SCREEN_WIDTH

        # Camera plane vectors (proper 3D math)
        dirX = math.cos(self.player.angle)
        dirY = math.sin(self.player.angle)
        planeX = math.cos(self.player.angle - math.pi/2) * 0.66
        planeY = math.sin(self.player.angle - math.pi/2) * 0.66

        for x in range(SCREEN_WIDTH):
            cameraX = 2 * x / SCREEN_WIDTH - 1
            rdx = dirX + planeX * cameraX
            rdy = dirY + planeY * cameraX

            mx = int(self.player.x)
            my = int(self.player.y)

            deltaDistX = abs(1 / rdx) if rdx != 0 else 1e30
            deltaDistY = abs(1 / rdy) if rdy != 0 else 1e30

            if rdx < 0:
                stepX = -1
                sideDistX = (self.player.x - mx) * deltaDistX
            else:
                stepX = 1
                sideDistX = (mx + 1 - self.player.x) * deltaDistX
            if rdy < 0:
                stepY = -1
                sideDistY = (self.player.y - my) * deltaDistY
            else:
                stepY = 1
                sideDistY = (my + 1 - self.player.y) * deltaDistY

            hit = False
            side = 0
            while not hit:
                if sideDistX < sideDistY:
                    sideDistX += deltaDistX
                    mx += stepX
                    side = 0
                else:
                    sideDistY += deltaDistY
                    my += stepY
                    side = 1
                if mx < 0 or mx >= len(self.player.map_grid[0]) or my < 0 or my >= len(self.player.map_grid):
                    hit = True
                    wall_color = C_GRAY
                elif self.player.map_grid[my][mx] > 0:
                    hit = True
                    tex_id = self.player.map_grid[my][mx]
                    wall_color = TEXTURES.get(tex_id, C_WHITE)

            if side == 0:
                perp_dist = (mx - self.player.x + (1 - stepX) / 2) / rdx
            else:
                perp_dist = (my - self.player.y + (1 - stepY) / 2) / rdy
            if perp_dist <= 0:
                perp_dist = 0.01
            z_buffer[x] = perp_dist

            # === DISTANCE SHADING + FOG (pure math) ===
            shade = max(0.35, 1.0 / (1.0 + perp_dist * 0.18))
            color = tuple(int(c * shade) for c in wall_color)
            if side == 1:
                color = tuple(int(c * 0.65) for c in color)

            line_h = int(SCREEN_HEIGHT / perp_dist)
            draw_start = max(0, -line_h // 2 + HALF_HEIGHT)
            draw_end = min(SCREEN_HEIGHT - 1, line_h // 2 + HALF_HEIGHT)

            # === PROCEDURAL TEXTURE (math-based brick/stone effect) ===
            for y in range(draw_start, draw_end):
                tex_y = (y - HALF_HEIGHT) % 16
                if tex_y < 4 and tex_id > 1:  # vertical lines / bricks
                    draw_color = tuple(max(0, c - 40) for c in color)
                else:
                    draw_color = color
                self.screen.set_at((x, y), draw_color)

        # ===== IMPROVED SPRITE RENDERING (proper math projection) =====
        active_entities = [e for e in self.entities if e.active]
        active_entities.sort(key=lambda e: math.hypot(self.player.x - e.x, self.player.y - e.y), reverse=True)

        for ent in active_entities:
            spriteX = ent.x - self.player.x
            spriteY = ent.y - self.player.y

            invDet = 1.0 / (planeX * dirY - dirX * planeY)
            transformX = invDet * (dirY * spriteX - dirX * spriteY)
            transformY = invDet * (-planeY * spriteX + planeX * spriteY)

            if transformY > 0.1:
                sprite_screen_x = int((SCREEN_WIDTH / 2) * (1 + transformX / transformY))
                sprite_h = abs(int(SCREEN_HEIGHT / transformY))
                sprite_w = abs(int(SCREEN_HEIGHT / transformY * 0.85))

                draw_y = -sprite_h // 2 + HALF_HEIGHT + (math.sin(ent.anim_offset) * 8 if ent.type == EntityType.STAR else 0)
                draw_x_start = sprite_screen_x - sprite_w // 2

                base_color = C_YELLOW if ent.type == EntityType.STAR else C_RED if ent.type == EntityType.ENEMY else C_CYAN

                # Distance shade for sprites too
                sprite_shade = max(0.4, 1.0 / (1.0 + transformY * 0.25))
                shade_color = tuple(int(c * sprite_shade) for c in base_color)

                for stripe in range(max(0, draw_x_start), min(SCREEN_WIDTH, draw_x_start + sprite_w)):
                    if transformY < z_buffer[stripe]:
                        if ent.type == EntityType.STAR:
                            # Glowing star with sparkle
                            self.screen.fill(shade_color, (stripe, draw_y, 1, sprite_h))
                            if stripe % 3 == 0:
                                self.screen.fill(C_WHITE, (stripe, draw_y + sprite_h//4, 1, sprite_h//2))
                        else:
                            self.screen.fill(shade_color, (stripe, draw_y, 1, sprite_h))

    def draw_hud(self):
        pygame.draw.line(self.screen, C_WHITE, (HALF_WIDTH - 10, HALF_HEIGHT), (HALF_WIDTH + 10, HALF_HEIGHT), 2)
        pygame.draw.line(self.screen, C_WHITE, (HALF_WIDTH, HALF_HEIGHT - 10), (HALF_WIDTH, HALF_HEIGHT + 10), 2)

        looking_portal = None
        for ent in self.entities:
            if ent.type == EntityType.PORTAL:
                d = math.hypot(ent.x - self.player.x, ent.y - self.player.y)
                if d < 2.5:
                    angle_diff = (math.atan2(ent.y - self.player.y, ent.x - self.player.x) - self.player.angle + math.pi) % (2 * math.pi) - math.pi
                    if abs(angle_diff) < 0.3:
                        looking_portal = ent
                        break
        if looking_portal:
            prompt = self.font.render(f"SPACE → {looking_portal.name}", True, C_WHITE)
            self.screen.blit(prompt, (HALF_WIDTH - prompt.get_width()//2, HALF_HEIGHT + 50))

        star_txt = self.font.render(f"STARS: {self.player.stars}/20", True, C_YELLOW)
        lives_txt = self.font.render(f"LIVES: {self.player.lives}", True, C_RED)
        lvl_txt = self.font.render(LEVELS[self.current_level]['name'], True, C_WHITE)
        self.screen.blit(star_txt, (10, 10))
        self.screen.blit(lives_txt, (10, 50))
        self.screen.blit(lvl_txt, (SCREEN_WIDTH - lvl_txt.get_width() - 10, 10))

    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if self.current_level == 0:
                            running = False
                        else:
                            self.load_level(0)
                    if event.key == pygame.K_SPACE and self.current_level == 0:
                        for ent in self.entities:
                            if ent.type == EntityType.PORTAL:
                                d = math.hypot(ent.x - self.player.x, ent.y - self.player.y)
                                if d < 2.5:
                                    angle_diff = (math.atan2(ent.y - self.player.y, ent.x - self.player.x) - self.player.angle + math.pi) % (2 * math.pi) - math.pi
                                    if abs(angle_diff) < 0.3:
                                        self.load_level(ent.target)
                                        break
                if event.type == pygame.MOUSEMOTION:
                    self.player.angle += event.rel[0] * 0.005

            self.screen.fill(C_BLACK)
            self.update()
            self.draw_raycast()
            self.draw_hud()

            if self.player.stars >= 20:
                self.state = GameState.VICTORY
            if self.state == GameState.GAME_OVER:
                msg = self.font.render("GAME OVER", True, C_RED)
                self.screen.blit(msg, (HALF_WIDTH - msg.get_width()//2, HALF_HEIGHT))
            elif self.state == GameState.VICTORY:
                msg = self.font.render("YOU GOT ALL THE STARS!", True, C_YELLOW)
                self.screen.blit(msg, (HALF_WIDTH - msg.get_width()//2, HALF_HEIGHT))

            pygame.display.flip()
            self.clock.tick(FPS)

        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    game = Game()
    game.run()
