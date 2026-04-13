import time
import unittest

from core.events import EventBus
from core.tasks import TaskManager


class TaskTests(unittest.TestCase):
    def test_task_manager_publishes_completion(self):
        bus = EventBus()
        tasks = TaskManager(bus, max_workers=1)

        self.assertTrue(tasks.submit("sum", lambda a, b: a + b, args=(2, 3)))

        deadline = time.time() + 1.0
        while time.time() < deadline:
            events = bus.drain()
            for event in events:
                if event.get("name") == "sum":
                    self.assertEqual(event.get("status"), "completed")
                    self.assertEqual(event.get("payload"), 5)
                    return
            time.sleep(0.01)

        self.fail("task completion event not received")


if __name__ == "__main__":
    unittest.main()
