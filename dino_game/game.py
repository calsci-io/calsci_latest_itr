"""Main Dino gameplay loop for CalSci."""

import time

from .config import (
    AUTO_PLAY,
    DAY_NIGHT_SWITCH_CYCLES,
    HI_SCORE_FILE,
    INCREASE_FPS_EVERY_N_SCORE_POINTS,
    LIVES_MAX,
    LIVES_START,
    RESET_HI_SCORE,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    SPLASH_WAIT_MS,
    SPLASH_WAIT_STEPS,
    TARGET_FPS_MAX,
    TARGET_FPS_START,
)
from .engine import BitCanvas, CollisionDetector, SpawnHold, Sprite, present
from . import assets
from .entities import Cactus, Ground, HeartLive, Pterodactyl, TrexPlayer


if hasattr(time, "ticks_ms"):
    ticks_ms = time.ticks_ms
    ticks_diff = time.ticks_diff
else:
    def ticks_ms():
        return int(time.time() * 1000)

    def ticks_diff(a, b):
        return a - b


if hasattr(time, "sleep_ms"):
    sleep_ms = time.sleep_ms
else:
    def sleep_ms(ms):
        time.sleep(ms / 1000.0)


class DinoGame:
    def __init__(self, display, read_input, auto_play=AUTO_PLAY):
        self.display = display
        self.read_input = read_input
        self.auto_play = auto_play
        self._use_hw_inverse = hasattr(display, "set_inverse")

        if RESET_HI_SCORE:
            self.hi_score = 0
            self._save_hi_score(0)
        else:
            self.hi_score = self._load_hi_score()

        self._set_inverse(False)

    def splash_screen(self):
        canvas = BitCanvas(bytearray(SCREEN_WIDTH * SCREEN_HEIGHT // 8), SCREEN_HEIGHT, SCREEN_WIDTH)
        canvas.render(Sprite(assets.splash_screen_bm, (0, 0)))
        present(self.display, canvas.buffer, invert=False)

        for _ in range(SPLASH_WAIT_STEPS):
            jump, _, back = self._poll_input()
            if back:
                return False
            if jump:
                return True
            sleep_ms(SPLASH_WAIT_MS)
        return True

    def play_round(self):
        result = self._game_loop(self.hi_score)
        self._save_hi_score(self.hi_score)
        return result

    def _poll_input(self):
        state = self.read_input()
        if state is None:
            return False, False, False

        if isinstance(state, dict):
            return bool(state.get("jump")), bool(state.get("duck")), bool(state.get("back"))

        if len(state) == 2:
            return bool(state[0]), bool(state[1]), False
        return bool(state[0]), bool(state[1]), bool(state[2])

    def _render_number(self, canvas, x, y, number):
        base = 10000
        digit_w = assets.digits[0].width
        while base:
            digit = (number // base) % 10
            canvas.render(Sprite(assets.digits[digit], (x, y)))
            base //= 10
            x += digit_w + 1

    def _game_loop(self, hi_score):
        canvas = BitCanvas(bytearray(SCREEN_WIDTH * SCREEN_HEIGHT // 8), SCREEN_HEIGHT, SCREEN_WIDTH)

        spawn_holder = SpawnHold()

        trex = TrexPlayer()
        ground1 = Ground(-1)
        ground2 = Ground(63)
        ground3 = Ground(127)
        cactus1 = Cactus(spawn_holder)
        cactus2 = Cactus(spawn_holder)
        pterodactyl1 = Pterodactyl(spawn_holder)
        heart_live = HeartLive()

        sprites = (
            ground1,
            ground2,
            ground3,
            cactus1,
            cactus2,
            pterodactyl1,
            heart_live,
            trex,
        )
        enemies = (cactus1, cactus2, pterodactyl1)

        game_over_sprite = Sprite(assets.game_over_bm, (15, 12))
        restart_icon_sprite = Sprite(assets.restart_icon_bm, (55, 25))
        hi_sprite = Sprite(assets.hi_score_bm, (44, 0))
        hearts_sprite = Sprite(assets.hearts_5x_bm, (95, 8))

        prv_t = ticks_ms()
        game_over = False
        score = 0
        target_fps = TARGET_FPS_START
        lives = LIVES_START
        night = False
        self._set_inverse(False)

        while True:
            jump_pressed, duck_pressed, back_pressed = self._poll_input()
            if back_pressed:
                if score > hi_score:
                    hi_score = score
                self.hi_score = hi_score
                self._set_inverse(False)
                return None

            canvas.clear(False)

            canvas.render(hi_sprite)
            self._render_number(canvas, 60, 0, hi_score)
            self._render_number(canvas, 95, 0, score)

            hearts_sprite.limit_render_width_to = 6 * lives + 1
            canvas.render(hearts_sprite)

            for sprite in sprites:
                canvas.render(sprite)

            if game_over:
                canvas.render(game_over_sprite)
                canvas.render(restart_icon_sprite)

            present(self.display, canvas.buffer, invert=night and not self._use_hw_inverse)

            if game_over:
                if score > hi_score:
                    hi_score = score
                self.hi_score = hi_score
                self._set_inverse(False)
                while True:
                    jump_pressed, _, back_pressed = self._poll_input()
                    if jump_pressed:
                        return hi_score
                    if back_pressed:
                        return None
                    sleep_ms(50)

            if (not trex.is_blinking()) and CollisionDetector.check_many(trex, enemies):
                if lives:
                    trex.blink()
                    lives -= 1
                else:
                    trex.die()
                    game_over = True
                    continue

            if lives < LIVES_MAX and CollisionDetector.check(trex, heart_live):
                lives += 1
                heart_live.eat()

            if not self.auto_play:
                if jump_pressed:
                    trex.jump()
                trex.duck(duck_pressed)
            else:
                trex_x_right = trex.x + (trex.bitmap.width if trex.bitmap else 0)
                if (
                    (cactus1.x <= trex_x_right + 5 and cactus1.x > trex_x_right)
                    or (cactus2.x <= trex_x_right + 5 and cactus2.x > trex_x_right)
                    or (
                        pterodactyl1.y > 30
                        and pterodactyl1.x <= trex_x_right + 5
                        and pterodactyl1.x > trex_x_right
                    )
                ):
                    trex.jump()

                trex.duck(
                    pterodactyl1.y <= 30
                    and pterodactyl1.y > 20
                    and pterodactyl1.x <= trex_x_right + 15
                    and pterodactyl1.x > trex.x
                )

            for sprite in sprites:
                sprite.step()

            if score < 0xFFFE:
                score += 1

            if (score % INCREASE_FPS_EVERY_N_SCORE_POINTS) == 0 and target_fps < TARGET_FPS_MAX:
                target_fps += 1

            if (score % DAY_NIGHT_SWITCH_CYCLES) == 0:
                night = not night
                self._set_inverse(night)

            frame_time = 1000 // target_fps
            while ticks_diff(ticks_ms(), prv_t) < frame_time:
                sleep_ms(1)
            prv_t = ticks_ms()

    def _set_inverse(self, enabled):
        if self._use_hw_inverse:
            try:
                self.display.set_inverse(bool(enabled))
            except Exception:
                self._use_hw_inverse = False

    def _load_hi_score(self):
        try:
            with open(HI_SCORE_FILE, "rb") as f:
                b = f.read(2)
                if len(b) == 2:
                    v = b[0] | (b[1] << 8)
                    if v != 0xFFFF:
                        return v
        except OSError:
            pass
        return 0

    def _save_hi_score(self, value):
        value &= 0xFFFF
        try:
            with open(HI_SCORE_FILE, "wb") as f:
                f.write(bytes((value & 0xFF, (value >> 8) & 0xFF)))
        except OSError:
            pass
