import pygame
from pygame._sdl2.video import Window, Renderer, Texture, Image
import pygame.gfxdraw
import sys
import asyncio
import os
from math import sin, cos, atan2, degrees, radians, hypot
import random
import json
import time
from os.path import join as path


# initializations
WHITE = (255, 255, 255, 255)
pygame.init()
WIDTH, HEIGHT = 1200, 800
win = Window(size=(WIDTH, HEIGHT), title="Particle Overdose")
ren = Renderer(win)
clock = pygame.time.Clock()
fps = 120
font = pygame.font.SysFont("Courier New", 30)
giga_font = pygame.font.SysFont("Copperplate", 60)
mini_font = pygame.font.SysFont("Courier New", 20)
fake_scroll = [0, 0]
scroll = [0, 0]
lag = 10
intro_sprs = []
for i in range(WIDTH):
    intro_img = pygame.Surface((WIDTH, HEIGHT))
    pygame.gfxdraw.filled_circle(intro_img, WIDTH // 2, HEIGHT // 2, i, WHITE)
    intro_img.set_colorkey(WHITE)
    tex = Texture.from_surface(ren, intro_img)
    intro_sprs.append(tex)
intro_rect = pygame.Rect(0, 0, WIDTH, HEIGHT)
bullet_sound = pygame.mixer.Sound(path("assets", "sounds", "bullet.wav"))
bullet_sound.set_volume(0.3)
death_sound = pygame.mixer.Sound(path("assets", "sounds", "death.wav"))
reload_sound = pygame.mixer.Sound(path("assets", "sounds", "reload.wav"))
reload_complete_sound = pygame.mixer.Sound(path("assets", "sounds", "reload_complete.wav"))
ray_gun_sound = pygame.mixer.Sound(path("assets", "sounds", "ray_gun.wav"))
spawn_sounds = [pygame.mixer.Sound(path("assets", "sounds", f"spawn{n}.wav")) for n in range(1, 2)]
lava_sound = pygame.mixer.Sound(path("assets", "sounds", "lava.wav"))
lava_sound.set_volume(0.5)
new_gun_sound = pygame.mixer.Sound(path("assets", "sounds", "new_gun.wav"))
for spawn_sound in spawn_sounds:
    spawn_sound.set_volume(0.2)
palette = [
	(227, 178, 178),
    (238, 216, 150),
	(151, 225, 179),
	(142, 192, 216),
	(207, 186, 234)
]
with open("guns.json") as f:
    gun_data = json.load(f)
    gun_names = list(x for x in gun_data.keys() if x[0] != "_")
    gun_categories = ("Pierce", "Mobility", "Firerate", "Reload", "Damage", "Ammo", "Mag")
    gun_maxes = {"Pierce": 1, "Mobility": 3, "Firerate": 937, "Reload": 1.9, "Damage": 1000, "Ammo": 500, "Mag": 125}

def load_asset(*path):
    surf = pygame.image.load(os.path.join(*path))
    surf = pygame.transform.scale(surf, [s * 3 for s in surf.get_size()])
    tex = Texture.from_surface(ren, surf)
    img = Image(tex)
    return img


def write(text, x, y, color="black", orien="topleft", font_=font):
    surf = font_.render(str(text), True, pygame.Color(color))
    tex = Texture.from_surface(ren, surf)
    tex_rect = tex.get_rect()
    setattr(tex_rect, orien, (x, y))
    ren.blit(tex, tex_rect)


def palettize(surf):
    return surf
    i = 0
    for y in range(surf.get_height()):
        for x in range(surf.get_width()):
            if surf.get_at((x, y)) != (0, 0, 0, 0):
                surf.set_at((x, y), palette[i])
            i += 1
            if i == len(palette):
                i = 0
    return surf


class Scrollable:
    def draw(self):
        self.scroll_rect.x = self.rect.x - scroll[0]
        self.scroll_rect.y = self.rect.y - scroll[1]
        ren.blit(self.img, self.scroll_rect)


class Tile(Scrollable):
    size = 30
    images = {name: Texture.from_surface(ren, pygame.transform.scale_by(palettize(pygame.image.load(path("assets", "tiles", f"{name}.png"))), 3)) for name in ("stone",)}
    def __init__(self, row, col, id_):
        self.row, self.col, self.id = row, col, id_
        self.x, self.y = self.row * Tile.size, self.col * Tile.size
        self.surf = pygame.Surface((Tile.size, Tile.size))
        self.surf.fill(random.choice(palette))
        self.lava = False
        if random.randint(1, 50) == 1:
            self.surf.fill((160, 160, 160))
            self.solid = True
        self.img = Texture.from_surface(ren, self.surf)
        self.rect = self.img.get_rect(topleft=(self.x, self.y))
        self.scroll_rect = self.rect.copy()

    def update(self):
        self.draw()

    def set_lava(self):
        self.surf = pygame.Surface((Tile.size, Tile.size))
        self.surf.fill((255, 95, 31))
        self.img = Texture.from_surface(ren, self.surf)
        self.lava = True


class Player(Scrollable):
    def __init__(self):
        self.w, self.h = 30, 30
        self.img = player_down[0]
        self.x, self.y = map_width / 2 * Tile.size, map_height / 2 * Tile.size
        self.rect = self.img.get_rect()
        self.scroll_rect = self.rect.copy()
        self.hp = 100
        self.points = 0
        self.anim = 0

    def key_input(self, dt):
        keys = pygame.key.get_pressed()
        mod = pygame.key.get_mods()
        v = 0.5 * dt * gun_data[gun.name]["mobility"]
        moved = False
        if keys[pygame.K_a]:
            self.x -= v
            moved = player_down
        if keys[pygame.K_d]:
            self.x += v
            moved = player_up
        if keys[pygame.K_w]:
            self.y -= v
            moved = player_up
        if keys[pygame.K_s]:
            self.y += v
            moved = player_down
        if moved:
            self.anim += 0.2
            if self.anim >= 12:
                self.anim = 0
            self.img = moved[int(self.anim)]

        # lava
        for tile in all_tiles:
            if tile.lava and self.rect.colliderect(tile.rect):
                self.hp -= 0.1
                self.img.color = (255, 0, 0)
                break
        else:
            self.img.color = (255, 255, 255)
        for bullet in all_bullets:
            if bullet.enemy and self.rect.colliderect(bullet.rect):
                self.hp -= 5
                self.img.color = (255, 0, 0)
                all_bullets.remove(bullet)
                break
        else:
            self.img.color = (255, 255, 255)
        for enemy in all_enemies:
            if self.rect.colliderect(enemy.rect):
                self.hp -= 0.1
                self.img.color = (255, 0, 0)
                break
        else:
            self.img.color = (255, 255, 255)

        # death
        if self.hp <= 0:
            death_sound.play()

        # final
        self.rect.topleft = (int(self.x), int(self.y))
        if self.rect.x < 0 or self.rect.x + self.w > map_width * Tile.size or self.rect.y < 0 or self.rect.y + self.h > map_height * Tile.size:
            self.hp -= 0.1
            player.img.color = (255, 0, 0)
        fake_scroll[0] += (self.rect.x - fake_scroll[0] - WIDTH // 2 + self.w // 2 ) / lag
        fake_scroll[1] += (self.rect.y - fake_scroll[1] - HEIGHT // 2 + self.h // 2) / lag
        scroll[0] = int(fake_scroll[0])
        scroll[1] = int(fake_scroll[1])

    def update(self, dt):
        self.key_input(dt)
        self.draw()


class Gun(Scrollable):
    images = {name: Image(Texture.from_surface(ren, pygame.transform.scale_by(palettize(pygame.image.load(path("assets/guns", f"{name}.png"))), 3))) for name in gun_names}
    def __init__(self):
        self.init("Colt M1911")

    def init(self, name):
        self.name = name
        self.mag = gun_data[self.name]["mag"]
        self.ammo = gun_data[self.name]["ammo"]
        self.img = Gun.images[self.name]
        self.img.origin = (self.img.texture.width / 2, self.img.texture.height / 2)
        self.rect = pygame.Rect(0, 0, self.img.texture.width, self.img.texture.height)
        self.scroll_rect = self.rect.copy()
        self.last_shot = time.perf_counter()
        self.reloading = False
        self.last_reload = time.perf_counter()

    @property
    def is_auto(self):
        return gun_data[self.name]["firerate"][0] == "auto"

    @property
    def fire_time(self):
        return 1 / (gun_data[self.name]["firerate"][1] / 60)

    def dynamize(self):
        # get mouse coordinates
        mouse = pygame.mouse.get_pos()
        # shoot a bullet
        self.angle = degrees(atan2(player.scroll_rect.centery - mouse[1], player.scroll_rect.centerx - mouse[0])) + 180
        mouses = pygame.mouse.get_pressed()
        if mouses[0] and self.is_auto:
            if time.perf_counter() - self.last_shot >= self.fire_time:
                self.shoot()
        # rotate the gun
        self.rect.center = player.rect.center
        self.img.angle = self.angle
        # flip the fun if necessary
        if mouse[0] < player.scroll_rect.centerx:
            self.img.flip_x = True
            self.img.angle += 180
        else:
            self.img.flip_x = False

    def shoot(self):
        if self.mag > 0:
            bullet = Bullet(*self.rect.center, 5, 5, self.angle, 10, gun_data[self.name]["fov"])
            all_bullets.append(bullet)
            self.mag -= 1
            self.last_shot = time.perf_counter()
            if self.name == "Ray Gun":
                ray_gun_sound.play()
            else:
                bullet_sound.play()
                cartridge = Particle(cartridge_img, *player.rect.center)
                all_particles.append(cartridge)
        elif self.ammo > 0:
            self.reload()

    def reload(self):
        if not self.reloading:
            self.reloading = True
            self.last_reload = time.perf_counter()
            reload_sound.play()

    def update(self):
        self.dynamize()
        self.draw()
        if self.reloading:
            write("[RELOADING]", player.scroll_rect.centerx, player.scroll_rect.centery - 105, "black", "center")
            if time.perf_counter() - self.last_reload >= gun_data[self.name]["reload"][int(self.ammo == 0)]:
                self.mag = gun_data[self.name]["mag"]
                self.ammo -= gun_data[self.name]["mag"]
                self.reloading = False
                reload_complete_sound.play()


class Bullet(Scrollable):
    def __init__(self, x, y, w, h, a, p, o=0, enemy=False):
        self.enemy = enemy
        self.x, self.y, self.w, self.h, = x, y, w, h
        self.surf = pygame.Surface((w, h))
        self.surf.fill((20, 20, 20))
        self.img = Texture.from_surface(ren, self.surf)
        self.img = Image(self.img)
        self.rect = self.surf.get_rect(topleft=(100, 100))
        self.scroll_rect = self.rect.copy()
        a += random.uniform(-o, o)
        a = radians(a)
        self.xvel = cos(a) * p
        self.yvel = sin(a) * p

    def dynamize(self, dt):
        self.x += self.xvel * dt
        self.y += self.yvel * dt
        if self.scroll_rect.right < 0 or self.scroll_rect.left >= WIDTH or self.scroll_rect.bottom < 0 or self.scroll_rect.top >= HEIGHT:
            all_bullets.remove(self)
        self.rect.topleft = (int(self.x), int(self.y))

    def update(self, dt):
        self.dynamize(dt)
        self.draw()


class Enemy(Scrollable):
    def __init__(self, row, col, speed):
        # init
        self.col, self.row = row, col
        self.x, self.y = row * Tile.size, col * Tile.size
        self.speed = speed
        self.fast = False
        self.img = enemy_imgs[0]
        if random.randint(1, 7) == 1:
            self.speed *= 2.5
            self.fast = True
            self.shooting_distance = random.randint(250, 500)
            self.shooting_delay = random.uniform(2.3, 2.9)
            self.img.color = (0, 255, 0)
        self.og_speed = self.speed
        self.last_shot = time.perf_counter()
        # images
        # final
        self.rect = self.img.get_rect()
        self.topleft = (x, y)
        self.scroll_rect = self.rect.copy()
        r = game_round - 1
        if game_round <= 9:
            self.hp = 150 + (r - 1) * 100
        else:
            self.hp = 150 + 9 * 100 * (r - 9) ** 1.1

    def dynamize(self, dt):
        self.angle = atan2(player.rect.centery - self.rect.centery, player.rect.centerx - self.rect.centerx)
        self.xvel = cos(self.angle) * self.speed
        self.yvel = sin(self.angle) * self.speed
        self.x += self.xvel * dt
        self.y += self.yvel * dt
        distance = abs(hypot(player.x - self.x, player.y - self.y))
        angle = degrees(atan2(player.y - self.y, player.x - self.x))
        if self.fast:
            if distance <= self.shooting_distance:
                self.speed = 0
                if time.perf_counter() - self.last_shot >= self.shooting_delay:
                    bullet = Bullet(*self.rect.center, 10, 10, angle, 3, 0, True)
                    all_bullets.append(bullet)
                    self.last_shot = time.perf_counter()
            else:
                self.speed = self.og_speed
        self.rect.topleft = (int(self.x), int(self.y))

    def collide(self):
        global round_active
        col = False
        for bullet in all_bullets:
            if not bullet.enemy and self.rect.colliderect(bullet.rect):
                self.hp -= gun_data[gun.name]["damage"]
                for _ in range(random.randint(2, 6)):
                    blood = Particle(blood_img, self.rect.centerx + random.uniform(-3, 3), self.rect.centery + random.uniform(-3, 3))
                    all_particles.append(blood)
                if self.hp <= 0:
                    all_enemies.remove(self)
                    if enemies_spawned == max_enemies and len(all_enemies) == 0:
                        round_active = False
                    return
                    player.points += 100
                else:
                    player.points += 20
                if not gun_data[gun.name]["pierce"]:
                    all_bullets.remove(bullet)
                col = True
        if col:
            self.img.color = (255, 0, 0)
        else:
            self.img.color = (255, 255, 255)

    def update(self, dt):
        self.dynamize(dt)
        self.collide()
        self.draw()


class Particle(Scrollable):
    def __init__(self, img, x, y):
        self.img = img
        if img == blood_img:
            self.img.angle = random.randint(1, 360)
        self.x, self.y = x, y
        self.rect = self.img.get_rect()
        self.rect.topleft = (self.x, self.y)
        self.scroll_rect = self.rect.copy()
        self.xvel = random.uniform(-1, 1)
        self.yvel = -5
        self.last_spawned = time.perf_counter()

    def dynamize(self, dt):
        if time.perf_counter() - self.last_spawned >= 0.3:
            all_particles.remove(self)
            return
        self.x += self.xvel * dt
        self.y += self.yvel * dt
        self.yvel += 0.3
        self.rect.topleft = (int(self.x), int(self.y))

    def update(self, dt):
        self.dynamize(dt)
        self.draw()


# player images
player_down_sprs = pygame.image.load("assets/player/player_down.png")
player_up_sprs = pygame.image.load("assets/player/player_up.png")
player_down = [Texture.from_surface(ren, pygame.transform.scale_by(player_down_sprs.subsurface(x * 11, 0, 10, 15), 3)) for x in range(12)]
player_up = [Texture.from_surface(ren, pygame.transform.scale_by(player_up_sprs.subsurface(x * 11, 0, 10, 15), 3)) for x in range(12)]

# game logic
map_width, map_height = 30, 30
all_bullets = []
all_particles = []
gun = Gun()
all_tiles = []
all_enemies = []
player = Player()
game_round = 1
round_active = False
round_alpha = 0
round_alpha_delta = 1
round_started = time.perf_counter()
last_lava = time.perf_counter()
gun_info = False
enemies_spawned = 0
max_enemies = 0
for y in range(map_width):
    for x in range(map_height):
        tile = Tile(x, y, "stone")
        all_tiles.append(tile)
pygame.mouse.set_visible(False)
cursor_img = pygame.transform.scale_by(pygame.image.load("assets/misc/cursor.png"), 3)
cartridge_img = load_asset("assets", "misc", "cartridge.png")
blood_img = load_asset("assets", "misc", "blood.png")
cursor_tex = Texture.from_surface(ren, cursor_img)
cursor_rect = cursor_tex.get_rect()
enemy_imgs = [load_asset(f"assets/misc/enemy{n}.png") for n in range(1, 2)]

# grid
grid = [
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0],
]
async def main():
    global game_round, round_active, round_alpha, round_alpha_delta, enemies_spawned, max_enemies, round_started, last_lava, gun_info
    intro_index = 0
    last_enemy = time.perf_counter()
    running = __name__ == "__main__"
    while running:
        dt = clock.tick(fps) / (1000 / 120)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    if not gun.is_auto:
                        gun.shoot()

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    gun.reload()

                elif event.key == pygame.K_SPACE:
                    if player.points >= 1000:
                        gun.init(random.choice(gun_names))
                        player.points -= 1000
                        new_gun_sound.play()

                elif event.key == pygame.K_i:
                    gun_info = not gun_info

        if round_active:
            if time.perf_counter() - last_enemy >= 0.3 and enemies_spawned < max_enemies:
                x, y = random.randint(0, map_width), random.randint(0, map_height)
                enemy = Enemy(x, y, 0.5)
                all_enemies.append(enemy)
                enemies_spawned += 1
                last_enemy = time.perf_counter()
                random.choice(spawn_sounds).play()

        ren.clear()
        ren.draw_color = (50, 50, 50, 255)
        ren.fill_rect((0, 0, WIDTH, HEIGHT))
        for tile in all_tiles:
            tile.update()
        if player.hp > 0:
            player.update(dt)
            gun.update()
        for bullet in all_bullets:
            bullet.update(dt)
        for enemy in all_enemies:
            enemy.update(dt)
        for particle in all_particles:
            particle.update(dt)

        w, h = WIDTH, 60
        ren.draw_color = (30, 30, 30, 120)
        ren.fill_rect((WIDTH / 2 - w / 2, 0, w, h))
        write(int(clock.get_fps()), 10, 10, "white")
        if player.hp > 0:
            write(f"HP: {int(player.hp)} | Points: {player.points}", WIDTH / 2, 8, "white", "midtop")
            write(f"{gun.mag} | {gun.ammo}", player.scroll_rect.centerx, player.scroll_rect.top - 45, "black" if gun.mag > 0 else "red", "center")
            if player.points >= 0:
                write("Space + 1000 points = random weapon | I = Gun info", WIDTH / 2, 35, "white", "midtop", mini_font)
        else:
            all_enemies.clear()
            write(f"Survived {game_round - 1} round{'s' if game_round - 1 > 1 else ''}", WIDTH / 2, HEIGHT / 2, "red", "center", giga_font)

        if not round_active:
            round_started = time.perf_counter()
            last_lava = time.perf_counter()
            max_enemies = 4 + (game_round - 1) * 5
            round_alpha += 1 * round_alpha_delta
            round_surf = giga_font.render(f"Round {game_round}", True, (200, 0, 0))
            round_surf.set_alpha(round_alpha)
            round_rect = round_surf.get_rect(center=(WIDTH / 2, HEIGHT / 2 + 55))
            round_tex = Texture.from_surface(ren, round_surf)
            ren.blit(round_tex, round_rect)
            if round_alpha >= 255:
                round_alpha_delta = -1
            if round_alpha <= 0:
                round_active = True
                game_round += 1
                enemies_spawned = 0
                round_alpha_delta = 1

        try:
            ren.blit(intro_sprs[intro_index], intro_rect)
            intro_index += 4
        except Exception:
            pass

        if gun_info:
            write(gun.name, WIDTH - 250, HEIGHT - 15 - 8 * 20, "black", "bottomleft", font)
            for y, cat in enumerate(gun_categories):
                if cat == "Reload":
                    continue
                write(cat, WIDTH - 250, HEIGHT - 15 - y * 20, "black", "bottomleft", mini_font)
                try:
                    ratio = gun_data[gun.name][cat.lower()] / gun_maxes[cat]
                except TypeError:
                    type_ = gun_data[gun.name][cat.lower()][0]
                    ratio = gun_data[gun.name]["firerate"][1] / gun_maxes["Firerate"]
                w = ratio * 100
                h = 10
                rect = pygame.Rect(WIDTH - 135, HEIGHT - 30 - y * 20, w, h)
                ren.draw_color = pygame.Color("#C1E1C1")
                ren.fill_rect(rect)
                ren.draw_color = (0, 0, 0, 0)
                ren.draw_rect(rect)

        if time.perf_counter() - round_started >= 15:
            if time.perf_counter() - last_lava >= 7:
                random.choice(all_tiles).set_lava()
                last_lava = time.perf_counter()
                lava_sound.play()

        cursor_rect.center = pygame.mouse.get_pos()
        ren.blit(cursor_tex, cursor_rect)

        ren.present()
        await asyncio.sleep(0)

    pygame.quit()
    sys.exit()


asyncio.run(main())
