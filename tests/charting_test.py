import sys, os.path
# a convoluted line to add hamster module to absolute path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import unittest
from hamster import graphics, charting

class TestIteratorFunctions(unittest.TestCase):
    def test_target_bigger(self):
        # targetting up
        integrator = graphics.Integrator(0)
        integrator.target(10)
        integrator.update()
        assert 0 < integrator.value < 10, "not going up as expected %f" \
                                                              % integrator.value
    def test_target_lesser(self):
        # targetting down
        integrator = graphics.Integrator(0)
        integrator.target(-10)
        integrator.update()
        assert -10 < integrator.value < 0, "not going down as expected %f" \
                                                              % integrator.value
    def test_reaches_target(self):
        # target is reached
        integrator = graphics.Integrator(0)
        integrator.target(10)

        while integrator.update():
            pass
        self.assertEquals(round(integrator.value, 0), 10)


class TestSizeListFunctions(unittest.TestCase):
    def test_values_stay(self):
        # on shrinkage, values are kept
        list_a = [1, [2, 3, 4], 5]
        list_b = [6, [7, 8]]
        res = charting.size_list(list_a, list_b)
        self.assertEquals(res, [1, [2, 3]])

    def test_grow(self):
        # source table expands
        list_a = [1, [2, 3], 4]
        list_b = [5, [6, 7, 8], 9, 10]
        res = charting.size_list(list_a, list_b)
        self.assertEquals(res , [1, [2, 3, 8], 4, 10])

class TestGetLimits(unittest.TestCase):
    def test_simple(self):
        min_v, max_v = charting.get_limits([4, 7, 2, 4, 6, 12, 3, 1, 9])
        # correct min
        self.assertEquals(min_v, 1)

        # correct max
        self.assertEquals(max_v, 12)

if __name__ == '__main__':
    unittest.main()
