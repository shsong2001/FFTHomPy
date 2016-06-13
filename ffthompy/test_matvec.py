import unittest
import numpy as np
from matvec import DFT, VecTri


class Test_matvec(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_matrix_versions(self):
        for dim in [2, 3]:
            for n in [4, 5]:
                N = n*np.ones(dim, dtype=np.int)
                ur = VecTri(name='rand', dim=2, N=N, valtype='rand')
                FN = DFT(name='FN', inverse=False, N=N, d=dim)
                FiN = DFT(name='FiN', inverse=True, N=N, d=dim)
                msg = 'Operations .matrix() .vec() do not work properly!'
                Fur = FN(ur)
                val = np.linalg.norm(Fur.vec()-FN.matrix().dot(ur.vec()))
                self.assertAlmostEqual(0, val, msg=msg, delta=1e-13)
                val = np.linalg.norm(ur.vec()-FiN.matrix().dot(Fur.vec()))
                self.assertAlmostEqual(0, val, msg=msg, delta=1e-13)

if __name__ == "__main__":
    unittest.main()