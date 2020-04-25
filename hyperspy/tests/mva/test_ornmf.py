import pytest
import numpy as np
from hyperspy.learn.ornmf import ornmf


def compare(a, b):
    n1, n2 = list(map(np.linalg.norm, [a, b]))
    return np.linalg.norm((a / n1) - (b / n2))


m = 512
n = 256
r = 3
tol = 5e-3 * m * n

rng = np.random.RandomState(101)
U = rng.uniform(0, 1, (m, r))
V = rng.uniform(0, 1, (r, n))
X = np.dot(U, V)
np.divide(X, max(1.0, np.linalg.norm(X)), out=X)

sparse = 0.05  # Fraction of corrupted pixels
E = 100 * rng.binomial(1, sparse, X.shape)
Y = X + E


def test_default():
    W, H = ornmf(X, r)
    res = compare(np.dot(W, H), X.T)
    print(res)
    assert res < tol


def test_corrupted_default():
    W, H = ornmf(Y, r)
    res = compare(np.dot(W, H), X.T)
    print(res)
    assert res < tol


def test_robust():
    W, H = ornmf(X, r, method='RobustPGD')
    res = compare(np.dot(W, H), X.T)
    print(res)
    assert res < tol


def test_corrupted_robust():
    W, H = ornmf(Y, r, method='RobustPGD')
    res = compare(np.dot(W, H), X.T)
    print(res)
    assert res < tol


def test_no_method():
    with pytest.raises(ValueError, match=f"'method' not recognised"):
        W, H = ornmf(X, r, method="uniform")


def test_subspace_tracking():
    W, H = ornmf(X, r, method='MomentumSGD')
    res = compare(np.dot(W, H), X.T)
    print(res)
    assert res < tol


@pytest.mark.parametrize("subspace_learning_rate", [None, 1.1])
def test_subspace_tracking_learning_rate(subspace_learning_rate):
    W, H = ornmf(X, r, method='MomentumSGD',
                 subspace_learning_rate=subspace_learning_rate)
    res = compare(np.dot(W, H), X.T)
    print(res)
    assert res < tol


@pytest.mark.parametrize("subspace_momentum", [None, 0.9])
def test_subspace_tracking_momentum(subspace_momentum):
    W, H = ornmf(X, r, method='MomentumSGD',
                 subspace_momentum=subspace_momentum)
    res = compare(np.dot(W, H), X.T)
    print(res)
    assert res < tol

    with pytest.raises(ValueError, match=f"must be a float between 0 and 1"):
        W, H = ornmf(X, r, method='MomentumSGD', subspace_momentum=1.9)

