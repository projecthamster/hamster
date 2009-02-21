import sys, os.path
# a convoluted line to add hamster module to absolute path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import unittest
from hamster import charting

class TestIteratorFunctions(unittest.TestCase):
    def test_target_bigger(self):
        integrator = charting.Integrator(0, 0)
        integrator.target(10)
        integrator.update()
        assert integrator.value == 1

    def test_target_lesser(self):
        integrator = charting.Integrator(0, 0)
        integrator.target(-10)
        integrator.update()
        assert integrator.value == -1
    
    def test_reaches_target(self):
        integrator = charting.Integrator(0, 0)
        integrator.target(10)
        
        while integrator.update():
            print integrator.value
        
        print round(integrator.value, 0)
        assert round(integrator.value, 0) == 10
        

if __name__ == '__main__':
    unittest.main()
