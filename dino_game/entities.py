"""Gameplay entities for the MicroPython Dino port."""

try:
    import urandom as _rand
except ImportError:
    import random as _rand

from .config import (
    CACTI_RESPAWN_RATE,
    GROUND_CACTI_SCROLL_SPEED,
    PLAYER_SAFE_ZONE_WIDTH,
    PTERODACTY_RESPAWN_RATE,
    PTERODACTY_SPEED,
    SPAWN_NEW_LIVE_MIN_CYCLES,
)
from .engine import ANCHOR_BOTTOM_LEFT, ScrollingSprite, SpriteAnimated, scale_value
from . import assets


def rand16():
    if hasattr(_rand, "getrandbits"):
        return _rand.getrandbits(16)
    return _rand.randint(0, 0xFFFF)


T_REX_JUMP_MOMENTUM = 8
T_REX_JUMP_MOMENTUM_DUCKED = 6
T_REX_START_X = 5
T_REX_START_Y = 60

TREX_SPRITES = (
    assets.trex_up_1,
    assets.trex_up_2,
    assets.trex_up_3,
    assets.trex_duck_1,
    assets.trex_duck_2,
    assets.trex_dead_1,
    assets.trex_dead_2,
)
T_REX_SPRITE_UP_START = 0
T_REX_SPRITE_UP_END = 3
T_REX_SPRITE_DUCK_START = 3
T_REX_SPRITE_DUCK_END = 5
T_REX_SPRITE_DEAD_UP = 5
T_REX_SPRITE_DEAD_DUCK = 6

GROUND_POSITION_Y = 64
GROUND_SPRITES = (
    assets.ground_1,
    assets.ground_2,
    assets.ground_3,
    assets.ground_4,
    assets.ground_5,
    assets.ground_1,
    assets.ground_2,
    assets.ground_3,
)

CACTUS_POSITION_Y = 61
CACTI_SPRITES = (
    assets.cacti_sb,
    assets.cacti_sb,
    assets.cacti_bs,
    assets.cacti_bs,
    assets.cacti_2b,
    assets.cacti_2b,
    assets.cacti_3s,
    assets.cacti_3s,
)
CACTI_WIDTH = (
    10,
    assets.cacti_sb.width,
    14,
    assets.cacti_bs.width,
    14,
    assets.cacti_2b.width,
    18,
    assets.cacti_3s.width,
)

PTERODACTYL_POSITION_Y1 = 15
PTERODACTYL_POSITION_Y2 = 25
PTERODACTYL_POSITION_Y3 = 35
PTERODACTYL_SPRITES = (assets.pterodactyl_1, assets.pterodactyl_2)
PTERODACTYL_Y_POSITIONS = (
    PTERODACTYL_POSITION_Y1,
    PTERODACTYL_POSITION_Y2,
    PTERODACTYL_POSITION_Y2,
    PTERODACTYL_POSITION_Y3,
)

HEART_MIN_Y = 15
HEART_DY = 35


class TrexPlayer(SpriteAnimated):
    UP = 0
    DUCK = 1
    DEAD = 2

    def __init__(self):
        super().__init__(TREX_SPRITES[0], (T_REX_START_X, T_REX_START_Y), ANCHOR_BOTTOM_LEFT)
        self.state = TrexPlayer.UP
        self.dy = 0
        self.vy = 0
        self.skip_step = False
        self.bitmap_id = 0
        self.blink_cnt = 0

    def step(self):
        self._animation_step()
        self._motion_step()

    def jump(self):
        if self._is_jumping() or self.state == TrexPlayer.DEAD:
            return
        self.vy = T_REX_JUMP_MOMENTUM if self.state == TrexPlayer.UP else T_REX_JUMP_MOMENTUM_DUCKED

    def duck(self, to_duck):
        if to_duck:
            if self.state == TrexPlayer.UP and not self._is_jumping():
                self.state = TrexPlayer.DUCK
        else:
            if self.state == TrexPlayer.DUCK:
                self.state = TrexPlayer.UP

    def die(self):
        self.bitmap = TREX_SPRITES[T_REX_SPRITE_DEAD_DUCK if self.state == TrexPlayer.DUCK else T_REX_SPRITE_DEAD_UP]
        self.state = TrexPlayer.DEAD
        self.vy = 0

    def blink(self):
        self.blink_cnt = PLAYER_SAFE_ZONE_WIDTH

    def is_blinking(self):
        return self.blink_cnt > 0

    def _is_jumping(self):
        return self.dy != 0 or self.vy != 0

    def _motion_step(self):
        if abs(self.vy) <= 1 and not self.skip_step:
            self.skip_step = True
            return
        self.skip_step = False

        self.dy += self.vy
        self.y -= self.vy
        if self.dy:
            self.vy -= 1
        else:
            self.vy = 0

    def _animation_step(self):
        if self.blink_cnt:
            self.blink_cnt -= 1
        if self.blink_cnt & 1:
            self.bitmap = None
            return

        if self.state == TrexPlayer.UP:
            start = T_REX_SPRITE_UP_START
            end = T_REX_SPRITE_UP_START if self._is_jumping() else T_REX_SPRITE_UP_END
        elif self.state == TrexPlayer.DUCK:
            start = T_REX_SPRITE_DUCK_START
            end = T_REX_SPRITE_DUCK_START if self._is_jumping() else T_REX_SPRITE_DUCK_END
        else:
            start = T_REX_SPRITE_DEAD_UP
            end = T_REX_SPRITE_DEAD_UP

        if not (self.bitmap_id >= start and self.bitmap_id < end):
            self.bitmap_id = start

        if self.bitmap_id + 1 < end:
            self.bitmap_id += 1
        else:
            self.bitmap_id = start

        self.bitmap = TREX_SPRITES[self.bitmap_id]


class Ground(ScrollingSprite):
    def __init__(self, start_x):
        super().__init__(GROUND_SPRITES[0], GROUND_CACTI_SCROLL_SPEED, GROUND_POSITION_Y, ANCHOR_BOTTOM_LEFT)
        self.x = start_x

    def step(self):
        for _ in range(self.speed):
            self.x -= 1
            if not self.is_active():
                self.bitmap = GROUND_SPRITES[rand16() & 7]
                self.rearm()


class Cactus(ScrollingSprite):
    def __init__(self, spawn_holder):
        super().__init__(CACTI_SPRITES[0], GROUND_CACTI_SCROLL_SPEED, CACTUS_POSITION_Y, ANCHOR_BOTTOM_LEFT)
        self.spawn_holder = spawn_holder
        self.respawn_wait = 0

    def step(self):
        super().step()
        if self.is_active():
            return

        if self.respawn_wait:
            self.respawn_wait -= 1
            return

        if not self.spawn_holder.try_acquire(self, PLAYER_SAFE_ZONE_WIDTH):
            return

        r = rand16()
        i = r & 7
        self.bitmap = CACTI_SPRITES[i]
        self.limit_render_width_to = CACTI_WIDTH[i]
        self.respawn_wait = scale_value(r & 0xFF, CACTI_RESPAWN_RATE)
        self.rearm()


class Pterodactyl(ScrollingSprite):
    def __init__(self, spawn_holder):
        super().__init__(PTERODACTYL_SPRITES[0], PTERODACTY_SPEED, PTERODACTYL_POSITION_Y1)
        self.spawn_holder = spawn_holder
        self.respawn_wait = 0
        self.animation_skip = 0

    def step(self):
        super().step()
        self._animation_step()
        if self.is_active():
            return

        if self.respawn_wait:
            self.respawn_wait -= 1
            return

        if not self.spawn_holder.try_acquire(self, PLAYER_SAFE_ZONE_WIDTH * 2):
            return

        r = rand16()
        self.y = PTERODACTYL_Y_POSITIONS[r & 3]
        half_rate = PTERODACTY_RESPAWN_RATE // 2
        self.respawn_wait = scale_value(r & 0xFF, half_rate) + half_rate
        self.rearm()

    def _animation_step(self):
        if self.animation_skip:
            self.animation_skip -= 1
            return
        self.animation_skip = 6
        if self.bitmap is PTERODACTYL_SPRITES[0]:
            self.bitmap = PTERODACTYL_SPRITES[1]
        else:
            self.bitmap = PTERODACTYL_SPRITES[0]


class HeartLive(ScrollingSprite):
    def __init__(self):
        super().__init__(assets.hearts_5x_bm, GROUND_CACTI_SCROLL_SPEED, HEART_MIN_Y)
        self.limit_render_width_to = 7
        self.respawn_wait = SPAWN_NEW_LIVE_MIN_CYCLES

    def step(self):
        super().step()
        if self.is_active():
            return

        if self.respawn_wait:
            self.respawn_wait -= 1
            return

        r = rand16()
        self.respawn_wait = SPAWN_NEW_LIVE_MIN_CYCLES + (r & 0xFF)
        self.y = HEART_MIN_Y + scale_value((r >> 6) & 0xFF, HEART_DY)
        self.rearm()

    def eat(self):
        self.x = -self.bitmap.width
