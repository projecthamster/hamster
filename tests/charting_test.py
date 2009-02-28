import sys, os.path
# a convoluted line to add hamster module to absolute path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import unittest
from hamster import graphics

class TestIteratorFunctions(unittest.TestCase):
    def test_target_bigger(self):
        integrator = graphics.Integrator(0, 0)
        integrator.target(10)
        integrator.update()
        assert 0 < integrator.value < 10, "not going up as expected %f" \
                                                              % integrator.value
    def test_target_lesser(self):
        integrator = graphics.Integrator(0, 0)
        integrator.target(-10)
        integrator.update()
        assert -10 < integrator.value < 0, "not going down as expected %f" \
                                                              % integrator.value
    def test_reaches_target(self):
        integrator = graphics.Integrator(0, 0)
        integrator.target(10)
        
        while integrator.update():
            pass
        assert round(integrator.value, 0) == 10

    
class TestSizeListFunctions(unittest.TestCase):
    def test_values_stay(self):
        list_a = [1, [2, 3, 4], 5]
        list_b = [6, [7, 8]]
        res = charting.size_list(list_a, list_b)
        assert res == [1, [2, 3]], "on shrinkage, values are kept, %s" % res

    def test_grow(self):
        list_a = [1, [2, 3], 4]
        list_b = [5, [6, 7, 8], 9, 10]
        res = charting.size_list(list_a, list_b)
        assert res == [1, [2, 3, 8], 4, 10], "source table expands, %s" % res

class TestGetLimits(unittest.TestCase):
    def test_simple(self):
        min_v, max_v = charting.get_limits([4, 7, 2, 4, 6, 12, 3, 1, 9])
        assert min_v == 1, "wrong minimal: %d" % min_v
        assert max_v == 12, "wrong maximal: %d" % max_v

if __name__ == '__main__':
    unittest.main()
