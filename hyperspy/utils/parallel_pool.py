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


import logging
import time
from multiprocessing import Pool, cpu_count
from multiprocessing.pool import Pool as Pool_type

try:
    import ipyparallel as ipp

    _ipyparallel_installed = True
except ImportError:
    _ipyparallel_installed = False


import numpy as np

_logger = logging.getLogger(__name__)


class ParallelPool:
    """Creates a ParallelPool by either looking for a ipyparallel client and
    then creating a load_balanced_view, or by creating a multiprocessing pool

    Attributes
    ----------
    pool : :class:`ipyparallel.LoadBalancedView` or :class:`python:multiprocessing.pool.Pool`
        The pool object.
    ipython_kwargs : dict
        The dictionary with Ipyparallel connection arguments.
    timeout : float
        Timeout for either pool when waiting for results.
    num_workers : int
        The number of workers actually created (may be less than requested, but
        can't be more).
    timestep : float
        Can be used as "ticks" to adjust CPU load when building upon this
        class.

    """

    _timestep = 0

    def __init__(self, num_workers=None, ipython_kwargs=None, ipyparallel=None):
        """Creates the ParallelPool and sets it up.

        Parameters
        ----------
        num_workers : None or int, default None
            The (max) number of workers to create. If less are available,
            smaller number is actually created.
        ipyparallel : None or bool, default None
            Which pool to set up. True - ipyparallel. False - multiprocessing.
            None - try ipyparallel, then multiprocessing if failed.
        ipython_kwargs : None or dict, default None
            Arguments that will be passed to the ipyparallel.Client when
            creating. Not None implies ipyparallel=True.
        """
        if ipython_kwargs is None:
            ipython_kwargs = {}
        else:
            ipyparallel = True
        self.timeout = 15.0
        self.ipython_kwargs = {"timeout": self.timeout}
        self.ipython_kwargs.update(ipython_kwargs)
        self.pool = None
        if num_workers is None:
            num_workers = np.inf
        self.num_workers = abs(num_workers)
        self.timestep = 0.001
        self.setup(ipyparallel=ipyparallel)

    def _timestep_get(self):
        return self._timestep

    def _timestep_set(self, value):
        value = np.abs(value)
        self._timestep = value

    timestep = property(lambda s: s._timestep_get(), lambda s, v: s._timestep_set(v))

    @property
    def is_ipyparallel(self):
        """Returns ``True`` if the pool is ipyparallel-based else ``False``."""
        return hasattr(self.pool, "client")

    @property
    def is_multiprocessing(self):
        """Returns ``True`` if the pool is multiprocessing-based else ``False``."""
        return isinstance(self.pool, Pool_type)

    @property
    def has_pool(self):
        """Returns ``True`` if the pool is ready and set-up else ``False``."""
        return self.is_ipyparallel or self.is_multiprocessing and self.pool._state == 0

    def _setup_ipyparallel(self):
        _logger.debug("Calling _setup_ipyparallel")
        try:
            ipyclient = ipp.Client(**self.ipython_kwargs)
            self.num_workers = min(self.num_workers, len(ipyclient))
            self.pool = ipyclient.load_balanced_view(range(self.num_workers))
            return True
        except OSError:
            _logger.debug("Failed to find ipyparallel pool")
            return False

    def _setup_multiprocessing(self):
        _logger.debug("Calling _setup_multiprocessing")
        self.num_workers = min(self.num_workers, cpu_count() - 1)
        self.pool = Pool(processes=self.num_workers)
        return True

    def setup(self, ipyparallel=None):
        """Sets up the pool.

        Parameters
        ----------
        ipyparallel : None or bool, default None
            If True, only tries to set up the ipyparallel pool. If False - only
            the multiprocessing. If None, first tries ipyparallel, and it does
            not succeed, then multiprocessing.
        """
        _logger.debug("Calling setup with ipyparallel={}".format(ipyparallel))
        if not self.has_pool:
            if not _ipyparallel_installed:
                if ipyparallel is True:
                    raise ValueError("ipyparralel must be installed")
                else:
                    _logger.info(
                        "ipyparallel is not installed, "
                        "a multiprocessing pool will be used."
                    )
                    ipyparallel = False
            if ipyparallel is True:
                if self._setup_ipyparallel():
                    return
                else:
                    raise ValueError("Could not connect to the ipyparallel Client")
            elif ipyparallel is False:
                self._setup_multiprocessing()
            elif ipyparallel is None:
                _ = self._setup_ipyparallel() or self._setup_multiprocessing()
                return
            else:
                raise ValueError("ipyparallel has to be True, False or None type")

    def sleep(self, howlong=None):
        """Sleeps for the required number of seconds.

        Parameters
        ----------
        howlong : None or float
            How long the pool should sleep for in seconds. If None (default),
            sleeps for "timestep".
        """
        if howlong is None:
            howlong = self.timestep
        time.sleep(howlong)
