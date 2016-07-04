# -*- coding: utf-8 -*-
# Copyright 2007-2016 The HyperSpy developers
#
# This file is part of  HyperSpy.
#
#  HyperSpy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
#  HyperSpy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with  HyperSpy.  If not, see <http://www.gnu.org/licenses/>.


import sys

import numpy as np
import numpy.testing as nt

import nose

import hyperspy.api as hs


real_ref = np.arange(9).reshape((3, 3))
imag_ref = np.arange(9).reshape((3, 3)) + 9
comp_ref = real_ref + 1j * imag_ref


class TestComplexProperties:

    def setUp(self):
        test = np.arange(9).reshape((3, 3)) + 1j * (9 + np.arange(9).reshape((3, 3)))
        self.s = hs.signals.BaseSignal(test)

    def test_get_real(self):
        nt.assert_almost_equal(self.s.real.data, real_ref)

    def test_set_real(self):
        test = np.random.random((3, 3))
        self.s.real = test
        nt.assert_almost_equal(self.s.real.data, test)

    def test_get_imag(self):
        nt.assert_almost_equal(self.s.imag.data, imag_ref)

    def test_set_imag(self):
        test = np.random.random((3, 3))
        self.s.imag = test
        nt.assert_almost_equal(self.s.imag.data, test)


if __name__ == '__main__':
    nose.run(argv=[sys.argv[0], sys.modules[__name__].__file__, '-v'])
