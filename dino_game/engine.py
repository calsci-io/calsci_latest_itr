"""Core rendering, collision, and utility types for the Dino game."""

ANCHOR_TOP_LEFT = 0
ANCHOR_BOTTOM_LEFT = 1


class BitmapMasked:
    __slots__ = ("width", "height", "data", "mask")

    def __init__(self, width, height, data, mask=None):
        self.width = width
        self.height = height
        self.data = data
        self.mask = mask

    @classmethod
    def from_blob(cls, bitmap_blob, mask_blob=None):
        width = bitmap_blob[0]
        height = bitmap_blob[1]
        size = width * ((height + 7) // 8)
        data = memoryview(bitmap_blob)[2:2 + size]
        mask = memoryview(mask_blob)[2:2 + size] if mask_blob else None
        return cls(width, height, data, mask)


class Sprite:
    __slots__ = ("bitmap", "x", "y", "anchor", "limit_render_width_to")

    def __init__(self, bitmap=None, position=(0, 0), anchor=ANCHOR_TOP_LEFT):
        self.bitmap = bitmap
        self.x = position[0]
        self.y = position[1]
        self.anchor = anchor
        self.limit_render_width_to = 0xFF


class SpriteAnimated(Sprite):
    def step(self):
        raise NotImplementedError


class ScrollingSprite(SpriteAnimated):
    __slots__ = ("speed", "reset_x")

    def __init__(self, bitmap, speed, position_y, anchor=ANCHOR_TOP_LEFT, reset_x=127):
        super().__init__(bitmap, (-127, position_y), anchor)
        self.speed = speed
        self.reset_x = reset_x

    def step(self):
        for _ in range(self.speed):
            if self.is_active():
                self.x -= 1

    def is_active(self):
        return self.x > -self.bitmap.width

    def rearm(self):
        self.x = self.reset_x


class BitCanvas:
    __slots__ = ("buffer", "height", "width", "x_offset", "y_offset")

    def __init__(self, bitmap_buffer, height, width):
        self.buffer = bitmap_buffer
        self.height = height
        self.width = width
        self.x_offset = 0
        self.y_offset = 0
        self.clear(False)

    def clear(self, value=False):
        fill = 0xFF if value else 0x00
        self.buffer[:] = bytes((fill,)) * len(self.buffer)

    def render(self, sprite):
        if sprite is None or sprite.bitmap is None:
            return

        bmp = sprite.bitmap
        s_x0 = sprite.x - self.x_offset
        s_x1 = s_x0 + min(bmp.width, sprite.limit_render_width_to)
        s_y0 = sprite.y - (bmp.height if sprite.anchor == ANCHOR_BOTTOM_LEFT else 0) - self.y_offset
        s_y1 = s_y0 + bmp.height

        if s_x0 >= self.width or s_x1 <= 0 or s_y0 >= self.height or s_y1 <= 0:
            return

        x_to = min(s_x1, self.width)
        y_to = min(s_y1, self.height)

        bit_offset = s_y0 % 8
        bmp_byte_height = (bmp.height + 7) // 8
        x_start = max(s_x0, 0)

        for y in range(max(s_y0, 0), 8 * ((y_to + 7) // 8), 8):
            y_byte = y // 8
            sy = y - s_y0
            sy_byte = (sy + 7) // 8

            row = y_byte * self.width

            mask_row = None
            mask_prev_row = None
            if bmp.mask is not None:
                if sy_byte < bmp_byte_height:
                    start = sy_byte * bmp.width
                    mask_row = bmp.mask[start:start + bmp.width]
                if sy_byte and (sy_byte - 1) < bmp_byte_height:
                    start = (sy_byte - 1) * bmp.width
                    mask_prev_row = bmp.mask[start:start + bmp.width]

            data_row = None
            data_prev_row = None
            if sy_byte < bmp_byte_height:
                start = sy_byte * bmp.width
                data_row = bmp.data[start:start + bmp.width]
            if sy_byte and (sy_byte - 1) < bmp_byte_height:
                start = (sy_byte - 1) * bmp.width
                data_prev_row = bmp.data[start:start + bmp.width]

            for x in range(x_start, x_to):
                sx = x - s_x0
                idx = row + x
                canvas_byte = self.buffer[idx]

                if mask_prev_row is not None:
                    canvas_byte &= ~((mask_prev_row[sx] >> (8 - bit_offset)) & 0xFF)
                if mask_row is not None:
                    canvas_byte &= ~((mask_row[sx] << bit_offset) & 0xFF)
                if data_prev_row is not None:
                    canvas_byte |= (data_prev_row[sx] >> (8 - bit_offset)) & 0xFF
                if data_row is not None:
                    canvas_byte |= (data_row[sx] << bit_offset) & 0xFF

                self.buffer[idx] = canvas_byte & 0xFF


class CollisionDetector:
    @staticmethod
    def check_many(sprite, sprites):
        for other in sprites:
            if CollisionDetector.check(sprite, other):
                return True
        return False

    @staticmethod
    def check(s1, s2):
        if s1 is None or s2 is None or s1.bitmap is None or s2.bitmap is None:
            return False

        w1 = s1.bitmap.width
        h1 = s1.bitmap.height

        s_x0 = s2.x - s1.x
        s_x1 = s_x0 + min(s2.bitmap.width, s2.limit_render_width_to)

        s_y0 = (
            s2.y
            - (s2.bitmap.height if s2.anchor == ANCHOR_BOTTOM_LEFT else 0)
            - s1.y
            + (h1 if s1.anchor == ANCHOR_BOTTOM_LEFT else 0)
        )
        s_y1 = s_y0 + s2.bitmap.height

        if s_x0 >= w1 or s_x1 <= 0 or s_y0 >= h1 or s_y1 <= 0:
            return False

        x_to = min(s_x1, w1)
        y_to = min(s_y1, h1)

        for y in range(max(s_y0, 0), y_to):
            y_byte = y // 8
            y_bit = y % 8
            sy = y - s_y0
            sy_byte = sy // 8
            sy_bit = sy % 8

            s1_row = y_byte * w1
            s2_row = sy_byte * s2.bitmap.width

            for x in range(max(s_x0, 0), x_to):
                sx = x - s_x0
                if (s1.bitmap.data[s1_row + x] & (1 << y_bit)) and (s2.bitmap.data[s2_row + sx] & (1 << sy_bit)):
                    return True

        return False


class SpawnHold:
    __slots__ = ("owner", "counter")

    def __init__(self):
        self.owner = None
        self.counter = 0

    def try_acquire(self, me, count_before_spawn):
        if self.owner is None:
            self.counter = count_before_spawn
            self.owner = me
            return False

        if self.owner is me:
            if self.counter:
                self.counter -= 1
                return False
            self.owner = None
            return True

        return False


def scale_value(value, limit):
    return (int(value) * int(limit)) >> 8


def present(display, src_buffer, invert=False):
    if hasattr(display, "graphics"):
        if not invert:
            display.graphics(src_buffer)
            return

        inv = getattr(display, "_dino_inv_buf", None)
        if inv is None or len(inv) != len(src_buffer):
            inv = bytearray(len(src_buffer))
            setattr(display, "_dino_inv_buf", inv)
        for i, b in enumerate(src_buffer):
            inv[i] = b ^ 0xFF
        display.graphics(inv)
        return

    width = getattr(display, "width", 128)
    height = getattr(display, "height", 64)

    if hasattr(display, "buffer") and len(display.buffer) == len(src_buffer):
        if invert:
            for i, b in enumerate(src_buffer):
                display.buffer[i] = b ^ 0xFF
        else:
            display.buffer[:] = src_buffer
        display.show()
        return

    for y in range(height):
        row = (y >> 3) * width
        bit = 1 << (y & 7)
        for x in range(width):
            pixel_on = 1 if (src_buffer[row + x] & bit) else 0
            if invert:
                pixel_on ^= 1
            display.pixel(x, y, pixel_on)
    display.show()
