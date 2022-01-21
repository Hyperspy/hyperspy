# -*- coding: utf-8 -*-
# Copyright 2007-2021 The HyperSpy developers
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
import numpy as np

from hyperspy.signal import BaseSignal
from hyperspy.drawing._markers.point import Point


class VectorSignal(BaseSignal):
    """A generic class for a ragged signal representing a set of vectors.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.vector = True

    def get_real_vectors(self, axis=None, real_units=True, flatten=False):
        """Returns the vectors in real units. Using the scale and offset as determined by the axes manager.
        If navigation axes are included the navigation axes will be transformed into vectors.

        Parameters
        ----------
        axis: None, int
            If None then the vectors for all axes will be returned. Otherwise, only the real units for
            the specified axes will be returned.
        flatten: bool
            If the vectors should be returned as one list or as a set of objects.
        pixel_units: bool
            Returns the vectors in pixel units rather than using the axes manager.
        """
        if axis is None:
            axes = self.axes_manager.signal_axes
        elif axis is "all":
            axes = self.axes_manager._axes
        else:
            axes = self.axes_manager[axis]
        nav_indexes = tuple([a.index_in_array for a in axes if a.navigate])
        sig_indexes = np.array([a.index_in_array for a in axes if not a.navigate])
        sig_indexes = tuple(sig_indexes - len(self.axes_manager.navigation_axes))
        navigate = any([a.navigate for a in axes])
        if not real_units:
            sig_scales = np.array([1 for a in axes if not a.navigate])
            sig_offsets = np.array([0 for a in axes if not a.navigate])
        else:
            sig_scales = np.array([a.scale for a in axes if not a.navigate])
            sig_offsets = np.array([a.offset for a in axes if not a.navigate])
        if not navigate:  # Only vector axes
            real_vector = np.empty(self.data.shape, dtype=object)
            for ind in np.ndindex(self.data.shape):
                vectors = self.data[ind][:,sig_indexes]
                real = vectors * sig_scales + sig_offsets
                real_vector[ind] = real
        elif len(sig_scales) == 0:  # Only navigation axes
            nav_positions = self._get_navigation_positions()
            # check to see if we need to find the navigation axis index...
            real_vector = nav_positions[:, :, nav_indexes]
        else:  # Both navigation and vector axes...
            nav_positions = self._get_navigation_positions(flatten=True)
            real_vector = np.empty(self.data.shape, dtype=object)
            for ind, nav_pos in zip(np.ndindex(self.data.shape), nav_positions):
                vectors = self.data[ind][:,sig_indexes]
                real = vectors * sig_scales + sig_offsets
                real_vector[ind] = np.array([tuple(nav_pos) + tuple(v)for v in real])
        if flatten:  # Unpack object into one array
            real_vector = np.array([v for ind in np.ndindex for v in real_vector[ind]])

        return real_vector

    def _get_navigation_positions(self, flatten=False, real_units=True):
        nav_indexes = np.array(list(np.ndindex(self.axes_manager.navigation_shape)))
        np.zeros(shape=self.axes_manager.navigation_shape)
        if not real_units:
            scales = [1 for a in self.axes_manager.navigation_axes]
            offsets = [0 for a in self.axes_manager.navigation_axes]
        else:
            scales = [a.scale for a in self.axes_manager.navigation_axes]
            offsets = [a.offset for a in self.axes_manager.navigation_axes]

        if flatten:
            real_nav = np.array([np.array(ind) * scales + offsets for ind in np.array(list(nav_indexes))])
        else:
            real_nav = np.reshape([np.array(ind) * scales + offsets for ind in np.array(list(nav_indexes))],
                                   self.axes_manager.navigation_shape+(-1,))
        return real_nav

    def cluster(self, func,
                axis="all", real_units=True,
                inplace=True,**kwargs):
        """
        Clusters the vectors based on the function given. This is a generic method
        for clustering some
        Parameters
        ----------
        method: func
            A function which returns labels for each of the
            vectors clustering. See sklearn.cluster
        navigation_to_vector
            Coverts each of the navigation axes to a vector
            to cluster in higher dimensions.
        **kwargs:
            Any additional keyword arguments for the method.
        Returns
        -------
        vector: Vector
            A collection of vectors clustered based on the function passed.
        """
        if inplace:
            vectors = self
        else:
            vectors = self.deepcopy()
        real_vectors = vectors.get_real_vectors(axis=axis,
                                                real_units=real_units,
                                                flatten=True)
        labels = func(real_vectors, **kwargs)
        groups = np.array([real_vectors[labels == l] for l in range(max(labels))], dtype=object)
        vectors.data = groups
        return vectors

    def to_markers(self,
                   x_axis=(-2,),
                   y_axis=(-1,),
                   **kwargs):
        """ Converts the vector to a set of markers given the axes.

        Parameters
        ----------
        x_axis: int
            The index for the x axis
        y_axis: int
            The index for the y axis
        """
        if isinstance(x_axis, int):
            x_axis = (x_axis,)
        if isinstance(y_axis, int):
            y_axis = (y_axis,)
        x_vectors = self.get_real_vectors(axis=x_axis).T
        y_vectors = self.get_real_vectors(axis=y_axis).T
        return Point(x_vectors, y_vectors,**kwargs)
