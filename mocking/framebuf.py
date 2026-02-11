from data_modules.characters import Characters

MONO_VLSB=0

class FrameBuffer:
    MVLSB = 0
    RGB565 = 1
    GS4_HMSB = 2
    MHLSB = 3
    MHMSB = 4
    GS2_HMSB = 5
    GS8 = 6
    
    def __init__(self, buffer, width, height, format, stride=None):
        self.buffer = buffer  # Must be bytearray or memoryview
        self.width = width
        self.height = height
        self.format = format
        self.stride = stride if stride else width
        
    def _setpixel(self, x, y, color):
        if self.format == self.MVLSB:
            index = (y >> 3) * self.stride + x
            offset = y & 0x07
            self.buffer[index] = (self.buffer[index] & ~(1 << offset)) | ((color != 0) << offset)
        elif self.format == self.RGB565:
            index = (x + y * self.stride) << 1
            self.buffer[index] = color & 0xFF
            self.buffer[index + 1] = (color >> 8) & 0xFF
        elif self.format == self.GS8:
            self.buffer[x + y * self.stride] = color & 0xFF
        elif self.format == self.GS4_HMSB:
            index = (x + y * self.stride) >> 1
            if x & 1:
                self.buffer[index] = (color & 0x0F) | (self.buffer[index] & 0xF0)
            else:
                self.buffer[index] = ((color & 0x0F) << 4) | (self.buffer[index] & 0x0F)
        elif self.format == self.GS2_HMSB:
            index = (x + y * self.stride) >> 2
            shift = (x & 0x3) << 1
            mask = 0x3 << shift
            self.buffer[index] = ((color & 0x3) << shift) | (self.buffer[index] & (~mask))
        elif self.format in (self.MHLSB, self.MHMSB):
            index = (x + y * self.stride) >> 3
            offset = (x & 7) if self.format == self.MHMSB else 7 - (x & 7)
            self.buffer[index] = (self.buffer[index] & ~(1 << offset)) | ((color != 0) << offset)
            
    def _getpixel(self, x, y):
        if self.format == self.MVLSB:
            return (self.buffer[(y >> 3) * self.stride + x] >> (y & 0x07)) & 1
        elif self.format == self.RGB565:
            index = (x + y * self.stride) << 1
            return self.buffer[index] | (self.buffer[index + 1] << 8)
        elif self.format == self.GS8:
            return self.buffer[x + y * self.stride]
        elif self.format == self.GS4_HMSB:
            index = (x + y * self.stride) >> 1
            if x & 1:
                return self.buffer[index] & 0x0F
            else:
                return self.buffer[index] >> 4
        elif self.format == self.GS2_HMSB:
            index = (x + y * self.stride) >> 2
            shift = (x & 0x3) << 1
            return (self.buffer[index] >> shift) & 0x3
        elif self.format in (self.MHLSB, self.MHMSB):
            index = (x + y * self.stride) >> 3
            offset = (x & 7) if self.format == self.MHMSB else 7 - (x & 7)
            return (self.buffer[index] >> offset) & 1
        return 0
            
    def pixel(self, x, y, color=None):
        if 0 <= x < self.width and 0 <= y < self.height:
            if color is None:
                return self._getpixel(x, y)
            else:
                self._setpixel(x, y, color)
                
    def fill(self, color):
        self.fill_rect(0, 0, self.width, self.height, color)
        
    def fill_rect(self, x, y, w, h, color):
        if h < 1 or w < 1:
            return
        x1 = max(0, x)
        y1 = max(0, y)
        x2 = min(self.width, x + w)
        y2 = min(self.height, y + h)
        
        for j in range(y1, y2):
            for i in range(x1, x2):
                self._setpixel(i, j, color)
                
    def hline(self, x, y, w, color):
        self.fill_rect(x, y, w, 1, color)
        
    def vline(self, x, y, h, color):
        self.fill_rect(x, y, 1, h, color)
        
    def rect(self, x, y, w, h, color, fill=False):
        if fill:
            self.fill_rect(x, y, w, h, color)
        else:
            self.hline(x, y, w, color)
            self.hline(x, y + h - 1, w, color)
            self.vline(x, y, h, color)
            self.vline(x + w - 1, y, h, color)
            
    def line(self, x1, y1, x2, y2, color):
        dx = x2 - x1
        sx = 1 if dx > 0 else -1
        dx = abs(dx)
        
        dy = y2 - y1
        sy = 1 if dy > 0 else -1
        dy = abs(dy)
        
        steep = dy > dx
        if steep:
            x1, y1 = y1, x1
            dx, dy = dy, dx
            sx, sy = sy, sx
            
        e = 2 * dy - dx
        for _ in range(dx):
            if steep:
                if 0 <= y1 < self.width and 0 <= x1 < self.height:
                    self._setpixel(y1, x1, color)
            else:
                if 0 <= x1 < self.width and 0 <= y1 < self.height:
                    self._setpixel(x1, y1, color)
            
            while e >= 0:
                y1 += sy
                e -= 2 * dx
            x1 += sx
            e += 2 * dy
            
        if 0 <= x2 < self.width and 0 <= y2 < self.height:
            self._setpixel(x2, y2, color)
                
    def ellipse(self, cx, cy, xr, yr, color, fill=False, mask=0x0F):
        if xr == 0 and yr == 0:
            if 0 <= cx < self.width and 0 <= cy < self.height:
                self._setpixel(cx, cy, color)
            return
            
        two_asq = 2 * xr * xr
        two_bsq = 2 * yr * yr
        x = xr
        y = 0
        xchg = yr * yr * (1 - 2 * xr)
        ychg = xr * xr
        err = 0
        stpx = two_bsq * xr
        stpy = 0
        
        while stpx >= stpy:
            self._draw_ellipse_pts(cx, cy, x, y, color, fill, mask)
            y += 1
            stpy += two_asq
            err += ychg
            ychg += two_asq
            if 2 * err + xchg > 0:
                x -= 1
                stpx -= two_bsq
                err += xchg
                xchg += two_bsq
                
        x = 0
        y = yr
        xchg = yr * yr
        ychg = xr * xr * (1 - 2 * yr)
        err = 0
        stpx = 0
        stpy = two_asq * yr
        
        while stpx <= stpy:
            self._draw_ellipse_pts(cx, cy, x, y, color, fill, mask)
            x += 1
            stpx += two_bsq
            err += xchg
            xchg += two_bsq
            if 2 * err + ychg > 0:
                y -= 1
                stpy -= two_asq
                err += ychg
                ychg += two_asq
                
    def _draw_ellipse_pts(self, cx, cy, x, y, color, fill, mask):
        if fill:
            if mask & 0x01:
                self.fill_rect(cx, cy - y, x + 1, 1, color)
            if mask & 0x02:
                self.fill_rect(cx - x, cy - y, x + 1, 1, color)
            if mask & 0x04:
                self.fill_rect(cx - x, cy + y, x + 1, 1, color)
            if mask & 0x08:
                self.fill_rect(cx, cy + y, x + 1, 1, color)
        else:
            if mask & 0x01 and 0 <= cx + x < self.width and 0 <= cy - y < self.height:
                self._setpixel(cx + x, cy - y, color)
            if mask & 0x02 and 0 <= cx - x < self.width and 0 <= cy - y < self.height:
                self._setpixel(cx - x, cy - y, color)
            if mask & 0x04 and 0 <= cx - x < self.width and 0 <= cy + y < self.height:
                self._setpixel(cx - x, cy + y, color)
            if mask & 0x08 and 0 <= cx + x < self.width and 0 <= cy + y < self.height:
                self._setpixel(cx + x, cy + y, color)
            
    def scroll(self, xstep, ystep):
        if abs(xstep) >= self.width or abs(ystep) >= self.height:
            return
            
        if xstep < 0:
            sx = 0
            xend = self.width + xstep
            dx = 1
        else:
            sx = self.width - 1
            xend = xstep - 1
            dx = -1
            
        if ystep < 0:
            y = 0
            yend = self.height + ystep
            dy = 1
        else:
            y = self.height - 1
            yend = ystep - 1
            dy = -1
            
        while y != yend:
            x = sx
            while x != xend:
                self._setpixel(x, y, self._getpixel(x - xstep, y - ystep))
                x += dx
            y += dy
            
    def text(self, s, x, y, color=1):
        from characters import Characters
        
        for char in s:
            chr_data = Characters.Chr2bytes(Characters, char)
            for j in range(5):
                if 0 <= x + j < self.width:
                    vline = chr_data[j]
                    for i in range(8):
                        if vline & (1 << i):
                            if 0 <= y + i < self.height:
                                self._setpixel(x + j, y + i, color)
            x += 6
