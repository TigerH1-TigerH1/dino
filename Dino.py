import pygame
from random import randint
import math

def tint_color(surface, color):
    tint = pygame.Surface(surface.get_size()).convert_alpha()
    tint.fill(color)
    result = surface.copy()
    result.blit(tint, (0, 0), special_flags=pygame.BLEND_MULT)
    return result

pygame.init()

WHITE = (255, 255, 255)
BG_COLOR = (247, 247, 247)
BLACK = (0, 0, 0)
dash_push = 0
FPS = 60

WIDTH, HEIGHT = 850, 400
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Chrome Dino (Pygame)")

# Якщо шрифту немає в папці, Pygame автоматично підставить системний дефолтний шрифт
try:
    pixel_font = pygame.font.Font("PressStart2P.ttf", 18)
    pixel_font_big = pygame.font.Font("PressStart2P.ttf", 32)
except IOError:
    pixel_font = pygame.font.SysFont("monospace", 18, bold=True)
    pixel_font_big = pygame.font.SysFont("monospace", 32, bold=True)

# -----------------------------
# СПРАЙТЫ
# -----------------------------
# Завантажуємо заглушки, якщо реальних картинок немає поруч з файлом
def load_img(path, size=(40, 40)):
    try:
        return pygame.image.load(path).convert_alpha()
    except pygame.error:
        surf = pygame.Surface(size, pygame.SRCALPHA)
        surf.fill((100, 100, 100))
        return surf

image_player_run1 = load_img("DinoRun1.png", (44, 47))
image_player_run2 = load_img("DinoRun2.png", (44, 47))
image_player_jump = load_img("DinoJump.png", (44, 47))

image_cactus1 = load_img("SmallCactus1.png", (34, 35))
image_cactus2 = load_img("SmallCactus2.png", (34, 35))
image_cactus3 = load_img("SmallCactus3.png", (34, 35))
cactus_images = [image_cactus1, image_cactus2, image_cactus3]

image_cloud = load_img("Cloud.png", (92, 27))
image_ground = load_img("Track.png", (1200, 12))
image_mountain = load_img("Mountain.png", (100, 60))

def scale_pixelart_clean(img, scale):
    w, h = img.get_width(), img.get_height()
    big = pygame.transform.scale(img, (w * 3, h * 3))
    new_w = int(w * scale)
    new_h = int(h * scale)
    final = pygame.transform.scale(big, (new_w, new_h))
    return final

raw_ptero1 = load_img("Ptero1.png", (46, 40))
raw_ptero2 = load_img("Ptero2.png", (46, 40))

image_ptero1 = scale_pixelart_clean(raw_ptero1, 1.5)
image_ptero2 = scale_pixelart_clean(raw_ptero2, 1.5)

GROUND_Y = 300
GROUND_LINE = GROUND_Y + 25

# -----------------------------
# БУРЯ + ВЕТЕР
# -----------------------------
storm_active = False
storm_intensity = 0
storm_timer = 0
storm_duration = 0
storm_cooldown = 0

dust_particles = []

wind_force = 0
wind_target = 0

# -----------------------------
# КРОВАВАЯ НОЧЬ
# -----------------------------
blood_night_active = False
blood_night_intensity = 0
blood_night_timer = 0
blood_night_duration = 0
blood_night_cooldown = 0

# -----------------------------
# ПТЕРО
# -----------------------------
def trim(img):
    rect = img.get_bounding_rect()
    if rect.width == 0 or rect.height == 0:
        return img
    return img.subsurface(rect).copy()

class Pterodactyl:
    def __init__(self, x, speed_factor):
        self.frames = [
            trim(image_ptero1),
            trim(image_ptero2)
        ]

        self.anim_index = 0
        self.frame_delay = 6
        self.frame_counter = 0

        base_y = GROUND_LINE - self.frames[0].get_height()
        heights = [
            base_y - 60,
            base_y - 45,
            base_y - 30
        ]
        self.y = heights[randint(0, 2)]

        self.rect = pygame.Rect(
            x, self.y,
            self.frames[0].get_width(),
            self.frames[0].get_height()
        )

        self.speed = 7 + speed_factor * 0.7

    def get_hitbox(self):
        w = int(self.rect.width * 0.55)
        h = int(self.rect.height * 0.55)
        return pygame.Rect(self.rect.left, self.rect.top, w, h)

    def update(self):
        global dash_push
        self.rect.x -= int(self.speed)
        if dash_push != 0:
            self.rect.x -= int(dash_push)

        self.frame_counter += 1
        if self.frame_counter >= self.frame_delay:
            self.frame_counter = 0
            self.anim_index ^= 1

    def draw(self, surface):
        surface.blit(self.frames[self.anim_index], self.rect)


# -----------------------------
# ИГРОК
# -----------------------------
class Player:
    def __init__(self, x):
        self.run_frames = [image_player_run1, image_player_run2]
        self.jump_frame = image_player_jump

        h = self.run_frames[0].get_height()
        y = GROUND_LINE - h

        self.max_y = y
        self.rect = pygame.Rect(x, y, self.run_frames[0].get_width(), h)

        self.velocity_y = 0
        self.GRAVITY = 1
        self.in_air = False

        self.anim_index = 0
        self.anim_timer = 0
        self.anim_speed = 0.18

        self.base_speed = 3
        self.slow_speed = 1

        # Дэш
        self.dash_speed = 22
        self.dash_duration = 8
        self.dash_timer = 0
        self.is_dashing = False

        self.dash_cooldown = 55
        self.dash_cooldown_timer = 0
        self.dash_direction = 1

        self.frozen_y = None

    def get_hitbox(self):
        return pygame.Rect(
            self.rect.left + 6,
            self.rect.top + 4,
            self.rect.width - 12,
            self.rect.height - 8
        )

    def update(self):
        global dash_push
        keys = pygame.key.get_pressed()

        move_speed = self.slow_speed if storm_active else self.base_speed

        # --- Запуск дэша ---
        if not self.is_dashing and self.dash_cooldown_timer == 0:
            if keys[pygame.K_RETURN]:
                if keys[pygame.K_RIGHT]:
                    self.dash_direction = 1
                elif keys[pygame.K_LEFT]:
                    self.dash_direction = -1
                else:
                    self.dash_direction = 1

                self.is_dashing = True
                self.dash_timer = self.dash_duration
                self.frozen_y = self.rect.top
                self.velocity_y = 0

        # --- Дэш ---
        if self.is_dashing:
            dash_push = self.dash_speed * self.dash_direction
            self.dash_timer -= 1

            if self.dash_timer > 2:
                self.rect.top += int((self.frozen_y - self.rect.top) * 0.35)
            else:
                self.rect.top += int((self.frozen_y - self.rect.top) * 0.12)

            if self.dash_timer <= 0:
                self.is_dashing = False
                self.dash_cooldown_timer = self.dash_cooldown

        elif self.dash_cooldown_timer > 0:
            self.dash_cooldown_timer -= 1

        # --- Обычное движение ---
        if not self.is_dashing:
            if keys[pygame.K_RIGHT]:
                self.rect.x += move_speed
            if keys[pygame.K_LEFT]:
                self.rect.x -= move_speed

        if storm_active:
            self.rect.x += int(wind_force * 0.4)

        # --- Прыжок и гравитация ---
        if not self.is_dashing:
            if (keys[pygame.K_SPACE] or keys[pygame.K_UP]) and not self.in_air:
                self.velocity_y = -21
                self.in_air = True

            self.velocity_y += self.GRAVITY
            self.rect.top += int(self.velocity_y)

            if self.rect.top >= self.max_y:
                self.rect.top = self.max_y
                self.velocity_y = 0
                self.in_air = False

        # --- Анимация ---
        if not self.in_air:
            self.anim_timer += self.anim_speed
            if self.anim_timer >= 1:
                self.anim_timer = 0
                self.anim_index ^= 1

    def draw(self, surface):
        img = self.jump_frame if self.in_air else self.run_frames[self.anim_index]
        surface.blit(img, self.rect)


# -----------------------------
# КАКТУСЫ
# -----------------------------
class Cactus:
    def __init__(self, x, speed):
        self.image = cactus_images[randint(0, 2)]
        h = self.image.get_height()
        y = GROUND_LINE - h
        self.rect = pygame.Rect(x, y, self.image.get_width(), h)
        self.speed = speed

    def get_hitbox(self):
        return pygame.Rect(
            self.rect.left + 4,
            self.rect.top + 4,
            self.rect.width - 8,
            self.rect.height - 4
        )

    def update(self):
        global dash_push
        self.rect.x -= int(self.speed)
        if dash_push != 0:
            self.rect.x -= int(dash_push)

    def draw(self, surface):
        surface.blit(self.image, self.rect)


# -----------------------------
# ОБЛАКА
# -----------------------------
class Cloud:
    def __init__(self, start=False):
        self.image = image_cloud
        cloud_y = randint(20, 200)
        cloud_x = randint(-900, WIDTH) if start else WIDTH
        self.rect = pygame.Rect(cloud_x, cloud_y, self.image.get_width(), self.image.get_height())
        self.speed = randint(1, 2)

    def update(self):
        self.rect.x -= int(self.speed + storm_intensity * 0.1 + wind_force * 0.5)

    def draw(self, surface):
        surface.blit(self.image, self.rect)


# -----------------------------
# ГОРА
# -----------------------------
class Mountain:
    def __init__(self):
        self.image = image_mountain
        scale = 2.2
        w = int(self.image.get_width() * scale)
        h = int(self.image.get_height() * scale)
        self.image = pygame.transform.scale(self.image, (w, h))

        self.rect = pygame.Rect(
            WIDTH + randint(200, 600),
            GROUND_Y - h + 133,
            w, h
        )
        self.speed = randint(1, 2)

    def update(self):
        self.rect.x -= self.speed

    def draw(self, surface):
        surface.blit(self.image, self.rect)


# -----------------------------
# ОКРУЖЕНИЕ
# -----------------------------
class Environment:
    def __init__(self):
        self.image = image_ground
        self.offset = 0

        self.clouds = [Cloud(start=True) for _ in range(8)]
        self.cloud_timer = 0

        self.mountains = []
        self.mountain_timer = 0
        self.mountain_interval = randint(900, 1500)

        first_mountain = Mountain()
        first_mountain.rect.x = WIDTH // 2 + 120
        self.mountains.append(first_mountain)

    def update(self, speed_factor):
        global dash_push

        speed = 9 + speed_factor
        self.offset -= int(speed + wind_force * 0.5)

        if dash_push != 0:
            self.offset -= int(dash_push)
            for m in self.mountains:
                m.rect.x -= int(dash_push * 0.15)
            for c in self.clouds:
                c.rect.x -= int(dash_push * 0.35)

            dash_push *= 0.8
            if abs(dash_push) < 0.5:
                dash_push = 0

        if self.offset <= -self.image.get_width():
            self.offset = 0

        self.mountain_timer += 1
        if self.mountain_timer >= self.mountain_interval:
            self.mountain_timer = 0
            self.mountain_interval = randint(900, 1500)
            self.mountains.append(Mountain())

        for m in self.mountains[:]:
            m.update()
            if m.rect.right < 0:
                self.mountains.remove(m)

        self.cloud_timer += 1
        if self.cloud_timer >= randint(100, 200):
            self.cloud_timer = 0
            self.clouds.append(Cloud())

        for c in self.clouds[:]:
            c.update()
            if c.rect.right < 0:
                self.clouds.remove(c)

    def draw(self, surface):
        shake = int(wind_force * 0.3)

        surface.blit(self.image, (self.offset, GROUND_Y + shake))
        surface.blit(self.image, (self.offset + self.image.get_width(), GROUND_Y + shake))

        for m in self.mountains:
            m.draw(surface)

        for c in self.clouds:
            c.draw(surface)


# -----------------------------
# ГРУППА КАКТУСОВ
# -----------------------------
class CactusGroup:
    def __init__(self, base_speed):
        self.spawn_timer = 0
        self.obstacles = []
        self.score = 0
        self.base_speed = base_speed

    def update(self, speed_factor):
        speed = self.base_speed + speed_factor

        self.spawn_timer += 1
        if self.spawn_timer >= randint(90, 160):
            self.spawn_timer = 0
            self.obstacles.append(Cactus(WIDTH + 20, speed))

        for o in self.obstacles[:]:
            o.speed = speed
            o.update()
            if o.rect.right < 0:
                self.obstacles.remove(o)
                self.score += 10

    def draw(self, surface):
        for o in self.obstacles:
            o.draw(surface)


# -----------------------------
# ВРАЖЕСКИЙ ДИНОЗАВР
# -----------------------------
class EnemyDino:
    def __init__(self, x, speed_factor):
        self.frames = [
            pygame.transform.flip(image_player_run1, True, False),
            pygame.transform.flip(image_player_run2, True, False)
        ]

        h = self.frames[0].get_height()
        self.rect = pygame.Rect(x, GROUND_LINE - h, self.frames[0].get_width(), h)
        self.speed = 7.5 + speed_factor * 0.5

        self.anim = 0
        self.anim_timer = 0
        self.armor_timer = 0
        self.pushback = 0

    def update(self, cactus_group):
        global dash_push

        move = self.speed
        if self.pushback > 0:
            move *= 0.5
            self.pushback -= 1

        self.rect.x -= int(move)
        if dash_push != 0:
            self.rect.x -= int(dash_push)

        collided = False
        for c in cactus_group.obstacles:
            if self.get_hitbox().colliderect(c.get_hitbox()):
                collided = True
                break

        if collided:
            self.armor_timer = 8
            self.pushback = 3

        if self.armor_timer > 0:
            self.armor_timer -= 1

        self.anim_timer += 1
        if self.anim_timer >= 6:
            self.anim_timer = 0
            self.anim = 1 - self.anim

    def draw(self, surface):
        img = self.frames[self.anim]
        shake = -2 if (self.armor_timer % 2 == 0 and self.armor_timer > 0) else 0
        surface.blit(img, (self.rect.x, self.rect.y + shake))

    def get_hitbox(self):
        return self.rect.inflate(-12, -8)


# -----------------------------
# СБРОС СОСТОЯНИЙ
# -----------------------------
def reset_storm():
    global storm_active, storm_intensity, storm_timer, storm_duration, storm_cooldown
    global dust_particles, wind_force, wind_target
    storm_active = False
    storm_intensity = 0
    storm_timer = 0
    storm_duration = 0
    storm_cooldown = 0
    dust_particles = []
    wind_force = 0
    wind_target = 0

def reset_blood_night():
    global blood_night_active, blood_night_intensity
    global blood_night_timer, blood_night_duration, blood_night_cooldown
    blood_night_active = False
    blood_night_intensity = 0
    blood_night_timer = 0
    blood_night_duration = 0
    blood_night_cooldown = 0


# -----------------------------
# ИНИЦИАЛИЗАЦИЯ
# -----------------------------
player = Player(40)
environment = Environment()
cactus_group = CactusGroup(base_speed=9)

pteros = []
enemy_dinos = []

clock = pygame.time.Clock()
running = True
game_over = False
high_score = 0

spawn_timer = 0
spawn_delay = 130
next_is_ptero = True

# Головна поверхня для малювання гри (потрібна для тонування Кривавої Ночі)
game_surface = pygame.Surface((WIDTH, HEIGHT))

# -----------------------------
# ГЛАВНЫЙ ЦИКЛ
# -----------------------------
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # КРОВАВАЯ НОЧЬ триггер
    if not storm_active and blood_night_cooldown == 0:
        if not blood_night_active and randint(1, 520) == 1:
            blood_night_active = True
            blood_night_duration = 10 * 60
            blood_night_timer = 0
            reset_storm()

    # БУРЯ триггер
    if storm_cooldown > 0:
        storm_cooldown -= 1

    if not storm_active and not blood_night_active and storm_cooldown == 0 and randint(1, 420) == 1:
        storm_active = True
        storm_duration = 8 * 60
        storm_timer = 0

    if storm_active:
        storm_timer += 1
        if storm_timer < storm_duration:
            storm_intensity = min(storm_intensity + 0.5, 30)
        else:
            storm_intensity -= 0.4
            if storm_intensity <= 0:
                storm_intensity = 0
                storm_active = False
                storm_cooldown = 420

        if randint(1, 20) == 1:
            wind_target = randint(-3, 3)

        wind_force += (wind_target - wind_force) * 0.05

        if randint(1, 2) == 1:
            dust_particles.append([
                randint(0, WIDTH),
                randint(0, HEIGHT),
                randint(2, 4),
                8 + storm_intensity * 0.4,
                255
            ])
    else:
        wind_force *= 0.9

    # ОБНОВЛЕНИЕ КРОВАВОЙ НОЧЬ
    if blood_night_active:
        blood_night_timer += 1
        if blood_night_timer < blood_night_duration:
            blood_night_intensity = min(blood_night_intensity + 0.4, 40)
        else:
            blood_night_intensity -= 0.4
            if blood_night_intensity <= 0:
                blood_night_intensity = 0
                blood_night_active = False
                blood_night_cooldown = 600

    # Часточки пилу бурі
    for p in dust_particles[:]:
        p[0] -= p[3] + wind_force
        p[4] -= 4
        if p[4] <= 0 or p[0] < -10:
            dust_particles.remove(p)

    if not game_over:
        speed_factor = cactus_group.score // 70

        player.update()
        environment.update(speed_factor)
        cactus_group.update(speed_factor)

        # ЧЕРЕДОВАНИЕ ПТЕРО / ЭНЕМИ
        spawn_timer += 1
        if spawn_timer >= spawn_delay:
            spawn_timer = 0
            if randint(0, 1) == 0:
                pteros.append(Pterodactyl(WIDTH + 20, speed_factor))
            else:
                spawn_x = WIDTH + 40
                min_dist = None
                for c in cactus_group.obstacles:
                    dist = c.rect.left - spawn_x
                    if dist < 0:
                        continue
                    if min_dist is None or dist < min_dist:
                        min_dist = dist

                if min_dist is not None and min_dist < 200:
                    spawn_x += (200 - min_dist)

                enemy_dinos.append(EnemyDino(spawn_x, speed_factor))

        for pt in pteros[:]:
            pt.update()
            if pt.rect.right < 0:
                pteros.remove(pt)
            elif player.get_hitbox().colliderect(pt.get_hitbox()):
                game_over = True
                high_score = max(high_score, cactus_group.score)

        for ed in enemy_dinos[:]:
            ed.update(cactus_group)
            if ed.rect.right < 0:
                enemy_dinos.remove(ed)
            elif player.get_hitbox().colliderect(ed.get_hitbox()):
                game_over = True
                high_score = max(high_score, cactus_group.score)

        for o in cactus_group.obstacles:
            if player.get_hitbox().colliderect(o.get_hitbox()):
                game_over = True
                high_score = max(high_score, cactus_group.score)
                break
    else:
        keys = pygame.key.get_pressed()
        if keys[pygame.K_r]:
            player = Player(40)
            environment = Environment()
            cactus_group = CactusGroup(base_speed=9)
            pteros = []
            enemy_dinos = []
            spawn_timer = 0
            next_is_ptero = True
            reset_storm()
            reset_blood_night()
            game_over = False

    # Малюємо все спочатку на віртуальну поверхню гри
    game_surface.fill(BG_COLOR)
    environment.draw(game_surface)
    cactus_group.draw(game_surface)

    for pt in pteros:
        pt.draw(game_surface)
    for ed in enemy_dinos:
        ed.draw(game_surface)

    player.draw(game_surface)

    for p in dust_particles:
        s = pygame.Surface((p[2], p[2]), pygame.SRCALPHA)
        s.fill((180, 180, 180, p[4]))
        game_surface.blit(s, (p[0], p[1]))

    # Ефект затемнення бурі
    if storm_intensity > 0:
        dark = pygame.Surface((WIDTH, HEIGHT))
        dark.fill((10, 10, 10))
        dark.set_alpha(min(int(storm_intensity * 2), 60))
        game_surface.blit(dark, (0, 0))

    # Візуалізація ефекту Кривавої Ночі через функцію тонування
    if blood_night_active:
        # Тонуємо картинку гри у червоний відтінок
        final_surface = tint_color(game_surface, (255, 120, 120))
    else:
        final_surface = game_surface
    

    

    # Виводимо фінальну картинку на реальний екран
    screen.blit(final_surface, (0, 0))

    # Інтерфейс (рахунок та текст) малюється поверх усього без спотворень кольору
    score_text = pixel_font.render(f"{cactus_group.score:05}", True, BLACK)
    screen.blit(score_text, (WIDTH - 150, 20))

    if high_score > 0:
        hi_text = pixel_font.render(f"HI {high_score:05}", True, BLACK)
        screen.blit(hi_text, (WIDTH - 300, 20))

    if game_over:
        go_text = pixel_font_big.render("GAME OVER", True, BLACK)
        screen.blit(go_text, (WIDTH // 2 - 180, HEIGHT // 2 - 40))

        restart_text = pixel_font.render("PRESS R TO RESTART", True, BLACK)
        screen.blit(restart_text, (WIDTH // 2 - 180, HEIGHT // 2 + 10))

    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()
