import unittest

from _helpers import fake_device_modules


class DisplayAdapterTests(unittest.TestCase):
    def test_draw_lines_renders_via_graphics_framebuffer(self):
        with fake_device_modules():
            from adapters.device.display import DeviceDisplayAdapter
            import st7565

            adapter = DeviceDisplayAdapter()
            adapter.init()
            adapter.set_invert(True)
            adapter.draw_lines(["CalSci", "Display"], selected_line=1, footer="ok")

            self.assertTrue(adapter._initialized)
            self.assertEqual(st7565._init_args, (9, 11, 10, 13, 12))
            self.assertTrue(st7565._inverted)
            self.assertIsNone(st7565._contrast)
            self.assertEqual(st7565._buffer, [])
            self.assertIsNotNone(st7565._graphics)
            self.assertEqual(len(st7565._graphics), 1024)
            self.assertTrue(any(value != 0 for value in st7565._graphics))


if __name__ == "__main__":
    unittest.main()
