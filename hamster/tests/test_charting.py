import sys; sys.path.insert(0, "../..")

import unittest
from hamster import charting

class TestIteratorFunctions(unittest.TestCase):
    def testOneStep(self):
        integrator = charting.Integrator(0)
        integrator.target(10)
        
        integrator.update()
        assert integrator.value == 9

if __name__ == '__main__':
    unittest.main()
