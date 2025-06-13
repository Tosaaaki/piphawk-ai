import unittest

from core.ring_buffer import RingBuffer


class TestRingBuffer(unittest.TestCase):
    def test_append_and_latest(self):
        rb = RingBuffer(3)
        rb.append(1)
        rb.append(2)
        rb.append(3)
        rb.append(4)
        self.assertEqual(rb.latest(), [4])
        self.assertEqual(rb.latest(2), [3, 4])
        self.assertEqual(len(rb), 3)


if __name__ == "__main__":
    unittest.main()
