import numpy as np
import scipy.linalg

import nose.tools as nt
from nose.plugins.skip import SkipTest

from hyperspy.learn.rpca import orpca

def _ev(U, L, atol=1e-3):
    # Check the similarity between the original
    # subspace basis and the OR-PCA results using
    # the "Expressed Variance" metric.
    # Perfect recovery of subspace: ev = 1
    C = np.dot(U, U.T)
    numer = np.trace(np.dot(L.T, np.dot(C, L)))
    denom = np.trace(C)
    return (1. - (numer / denom) < atol)

class TestORPCA:
    def setUp(self):
        # Define shape etc.
        m = 128  # Dimensionality
        n = 1024 # Number of samples
        r = 3
        s = 0.01

        # Low-rank and sparse error matrices
        rng = np.random.RandomState(101)
        U = scipy.linalg.orth(rng.randn(m, r))
        V = rng.randn(n, r)
        A = np.dot(U, V.T)
        E = 100 * rng.binomial(1, s, (m, n))
        X = A + E
        print('Amax is %f, Amin is %f' % (np.max(A),np.min(A)))
        print('Emax is %f, Emin is %f'% (np.max(E),np.min(E)))
        print('Xmax is %f, Xmin is %f'% (np.max(X),np.min(X)))

        self.m = m
        self.n = n
        self.rank = r
        self.lambda1 = 1 / np.sqrt(m)
        self.lambda2 = 1 / np.sqrt(m)
        self.U = U
        self.A = A
        self.E = E
        self.X = X

        # Test tolerance
        self.tol = 1e-3

    def test_default(self):
        L, R, E, U, S, V = orpca(self.X, rank=self.rank)

        # Check the low-rank component
        normA = np.linalg.norm(np.dot(L, R) - self.A) / (self.m * self.n)
        nt.assert_true(normA < self.tol)

        # Check the expressed variance of the
        # recovered subspace
        nt.assert_true(_ev(self.U, L, self.tol))

    def test_mask(self):
        L, R, E, U, S, V = orpca(self.X, rank=self.rank,
                                 mask=self.E)

        # Check the low-rank component
        normA = np.linalg.norm(np.dot(L, R) - self.A) / (self.m * self.n)
        nt.assert_true(normA < self.tol)

        # Check the expressed variance of the
        # recovered subspace
        nt.assert_true(_ev(self.U, L, self.tol))

    def test_regularization(self):
        L, R, E, U, S, V = orpca(self.X, rank=self.rank,
                                 lambda1=self.lambda1, lambda2=self.lambda2)

        # Check the low-rank component
        normA = np.linalg.norm(np.dot(L, R) - self.A) / (self.m * self.n)
        nt.assert_true(normA < self.tol)

        # Check the expressed variance of the
        # recovered subspace
        nt.assert_true(_ev(self.U, L, self.tol))

    def test_method(self):
        L, R, E, U, S, V = orpca(self.X, rank=self.rank, method='BCD')

        #  Check the low-rank component
        normA = np.linalg.norm(np.dot(L, R) - self.A) / (self.m * self.n)
        nt.assert_true(normA < self.tol)

        # Check the expressed variance of the
        # recovered subspace
        nt.assert_true(_ev(self.U, L, self.tol))


if __name__ == "__main__":
    test = TestORPCA()
    test.setUp()
    test.test_default()
    test.test_mask()
    test.test_method()
    test.test_regularization()
