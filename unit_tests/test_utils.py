import unittest
from madt_lib.utils import ceil_power_of_2, is_private


class TestUtil(unittest.TestCase):
	def test_ceil(self):
		with self.assertRaises(TypeError):
			ceil_power_of_2('1')
		self.assertEqual(3, ceil_power_of_2(8))

	def test_is_private(self):
		self.assertTrue(is_private('10.0.0.0'))


if __name__ == '__main__':
	unittest.main()
