#!/usr/bin/env python
import unittest
from hamster import charting

class TestIteratorFunctions(unittest.TestCase):
    def testOneStep(self):
        integrator = hamster.Integrator(0)
        integrator.target(10)
        
        integrator.update()
        assert integrator.value == 9

if __name__ == '__main__':
    unittest.main()
