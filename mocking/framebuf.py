"""
Mock framebuf module for simulator.
Provides a FrameBuffer class that mimics MicroPython's framebuf module
for desktop Python simulation.
"""

# Format constants
MONO_VLSB = 0  # Monochrome, vertical LSB format
MONO_HLSB = 1
MONO_HMSB = 2
RGB565 = 3


class FrameBuffer:
    """Mock FrameBuffer class for simulator."""

    def __init__(self, buffer, width, height, format):
        """Initialize framebuffer with buffer, dimensions, and format."""
        self.buffer = buffer
        self.width = width
        self.height = height
        self.format = format

    def pixel(self, x, y, color=None):
        """Get or set a pixel."""
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return

        if self.format == MONO_VLSB:
            # Vertical LSB: 8 pixels per byte, organized vertically
            byte_index = (x + (y // 8) * self.width)
            bit_index = y % 8
            if color is None:
                # Get pixel
                return (self.buffer[byte_index] >> bit_index) & 1
            else:
                # Set pixel
                if color:
                    self.buffer[byte_index] |= (1 << bit_index)
                else:
                    self.buffer[byte_index] &= ~(1 << bit_index)

    def fill(self, color):
        """Fill entire framebuffer with a color."""
        if color:
            for i in range(len(self.buffer)):
                self.buffer[i] = 0xFF
        else:
            for i in range(len(self.buffer)):
                self.buffer[i] = 0x00

    def hline(self, x, y, width, color):
        """Draw a horizontal line."""
        for i in range(width):
            if 0 <= x + i < self.width:
                self.pixel(x + i, y, color)

    def vline(self, x, y, height, color):
        """Draw a vertical line."""
        for i in range(height):
            if 0 <= y + i < self.height:
                self.pixel(x, y + i, color)

    def line(self, x0, y0, x1, y1, color):
        """Draw a line using Bresenham algorithm."""
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x1 > x0 else -1
        sy = 1 if y1 > y0 else -1
        err = dx - dy

        x, y = x0, y0
        while True:
            self.pixel(x, y, color)
            if x == x1 and y == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x += sx
            if e2 < dx:
                err += dx
                y += sy

    def rect(self, x, y, width, height, color, fill=False):
        """Draw a rectangle."""
        if fill:
            for i in range(height):
                self.hline(x, y + i, width, color)
        else:
            self.hline(x, y, width, color)
            self.hline(x, y + height - 1, width, color)
            self.vline(x, y, height, color)
            self.vline(x + width - 1, y, height, color)

    def text(self, text, x, y, color):
        """Draw text (basic implementation - no actual font rendering)."""
        # For simulator, we just skip text rendering or log it
        # In real MicroPython with font, this would render text
        pass

    def blit(self, source, x, y, key=-1, palette=None):
        """Blit another framebuffer onto this one."""
        pass
