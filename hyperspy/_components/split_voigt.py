# -*- coding: utf-8 -*-
# Copyright 2007-2024 The HyperSpy developers
#
# This file is part of HyperSpy.
#
# HyperSpy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# HyperSpy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with HyperSpy. If not, see <https://www.gnu.org/licenses/#GPL>.

import numpy as np

from hyperspy._components.gaussian import _estimate_gaussian_parameters
from hyperspy.component import Component, _get_scaling_factor
from hyperspy.docstrings.parameters import FUNCTION_ND_DOCSTRING

sqrt2pi = np.sqrt(2 * np.pi)


class SplitVoigt(Component):
    r"""Split pseudo-Voigt component.

    .. math::
        :nowrap:

        \[
        pV(x,centre,\sigma) = (1 - \eta) G(x,centre,\sigma)
        + \eta L(x,centre,\sigma)
        \]


        \[
        f(x) =
        \begin{cases}
            pV(x,centre,\sigma_1), & x \leq centre\\
            pV(x,centre,\sigma_2), & x >  centre
        \end{cases}
        \]

    ================= ===========
    Variable           Parameter
    ================= ===========
    :math:`A`          A
    :math:`\eta`       fraction
    :math:`\sigma_1`   sigma1
    :math:`\sigma_2`   sigma2
    :math:`centre`     centre
    ================= ===========

    Notes
    -----
    This is a voigt function in which the upstream and downstream variance or
    sigma is allowed to vary to create an asymmetric profile
    In this case the voigt is a pseudo voigt consisting of a
    mixed gaussian and lorentzian sum

    """

    def __init__(self, A=1.0, sigma1=1.0, sigma2=1.0, fraction=0.0, centre=0.0):
        Component.__init__(self, ("A", "sigma1", "sigma2", "centre", "fraction"))
        self.A.value = A
        self.sigma1.value = sigma1
        self.sigma2.value = sigma2
        self.centre.value = centre
        self.fraction.value = fraction
        self._position = self.centre

        # Boundaries
        self.A.bmin = 1.0e-8
        self.A.bmax = 1e8
        self.sigma2.bmin = 1.0e-8
        self.sigma2.bmax = 50.0
        self.sigma1.bmin = 1.0e-8
        self.sigma1.bmax = 50.0
        self.fraction.bmin = 1.0e-8
        self.fraction.bmax = 1.0
        self.isbackground = False
        self.convolved = True

    def _function(self, x, A, sigma1, sigma2, centre, fraction):
        arg = x - centre
        lor1 = (A / (1.0 + ((1.0 * arg) / sigma1) ** 2)) / (
            0.5 * np.pi * (sigma1 + sigma2)
        )
        lor2 = (A / (1.0 + ((1.0 * arg) / sigma2) ** 2)) / (
            0.5 * np.pi * (sigma1 + sigma2)
        )

        prefactor = A / (sqrt2pi * 0.5 * (sigma1 + sigma2))
        gauss1 = prefactor * np.exp(-0.5 * arg * arg / (sigma1 * sigma1))
        gauss2 = prefactor * np.exp(-0.5 * arg * arg / (sigma2 * sigma2))

        p1 = (1.0 - fraction) * gauss1 + fraction * lor1
        p2 = (1.0 - fraction) * gauss2 + fraction * lor2

        return np.where(x <= centre, p1, p2)

    def function(self, x):
        """Split pseudo voigt - a linear combination  of gaussian and lorentzian

        Parameters
        ----------
        x : array
            independent variable
        A : float
            area of pvoigt peak
        center : float
            center position
        sigma1 : float
            standard deviation <= center position
        sigma2 : float
            standard deviation > center position
        fraction : float
            weight for lorentzian peak in the linear combination,
            and (1-fraction) is the weight for gaussian peak.
        """
        parameters_value = [p.value for p in self.parameters]
        return self._function(x, *parameters_value)

    def function_nd(self, axis, parameters_values=None):
        """
        Calculate the component over given axes and with given parameter values.

        Parameters
        ----------
        axis : numpy.ndarray
            The axis onto which the component is calculated.
        %s

        Returns
        -------
        numpy.ndarray
            The component values.
        """
        if self._is_navigation_multidimensional:
            if parameters_values is None:
                parameters_values = [p.map["values"] for p in self.parameters]
            parameters_values = [p[..., np.newaxis] for p in parameters_values]
            return self._function(axis[np.newaxis, :], *parameters_values)
        else:
            return self.function(axis)

    function_nd.__doc__ %= FUNCTION_ND_DOCSTRING

    def estimate_parameters(self, signal, x1, x2, only_current=False):
        """Estimate the split voigt function by calculating the
           momenta the gaussian.

        Parameters
        ----------
        signal : :class:`~.api.signals.Signal1D`
        x1 : float
            Defines the left limit of the spectral range to use for the
            estimation.
        x2 : float
            Defines the right limit of the spectral range to use for the
            estimation.

        only_current : bool
            If False estimates the parameters for the full dataset.

        Returns
        -------
        bool

        Notes
        -----
        Adapted from https://scipy-cookbook.readthedocs.io/items/FittingData.html

        Examples
        --------

        >>> g = hs.model.components1D.SplitVoigt()
        >>> x = np.arange(-10, 10, 0.01)
        >>> data = np.zeros((32, 32, 2000))
        >>> data[:] = g.function(x).reshape((1, 1, 2000))
        >>> s = hs.signals.Signal1D(data)
        >>> s.axes_manager[-1].offset = -10
        >>> s.axes_manager[-1].scale = 0.01
        >>> g.estimate_parameters(s, -10, 10, False)
        True

        """
        super()._estimate_parameters(signal)
        axis = signal.axes_manager.signal_axes[0]
        centre, height, sigma = _estimate_gaussian_parameters(
            signal, x1, x2, only_current
        )
        scaling_factor = _get_scaling_factor(signal, axis, centre)

        if only_current is True:
            self.centre.value = centre
            self.sigma1.value = sigma
            self.sigma2.value = sigma
            self.A.value = height * sigma * sqrt2pi
            if axis.is_binned:
                self.A.value /= scaling_factor
            return True
        else:
            if self.A.map is None:
                self._create_arrays()
            self.A.map["values"][:] = height * sigma * sqrt2pi
            if axis.is_binned:
                self.A.map["values"][:] /= scaling_factor
            self.A.map["is_set"][:] = True
            self.sigma1.map["values"][:] = sigma
            self.sigma1.map["is_set"][:] = True
            self.sigma2.map["values"][:] = sigma
            self.sigma2.map["is_set"][:] = True
            self.centre.map["values"][:] = centre
            self.centre.map["is_set"][:] = True
            self.fraction.map["is_set"][:] = True
            self.fetch_stored_values()
            return True

    @property
    def _sigma(self):
        return (self.sigma1.value + self.sigma2.value) * 0.5

    @property
    def height(self):
        return self.A.value / (self._sigma * sqrt2pi)

    @height.setter
    def height(self, value):
        self.A.value = value * self._sigma * sqrt2pi
