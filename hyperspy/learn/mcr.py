import numpy as np
from pymcr.mcr import McrAR
from pymcr.constraints import ConstraintNonneg, ConstraintNorm
from hyperspy.misc.machine_learning.orthomax import orthomax
from hyperspy.misc.utils import stack
import logging
from contextlib import redirect_stdout
import io

_logger = logging.getLogger(__name__)


def mcrals(self,
           number_of_components=None,
           simplicity='spatial',
           mask=None,
           compute=False,
           verbosity='error',
           c_regr='OLS',
           st_regr='OLS',
           max_iter=100,
           c_constraints=[ConstraintNonneg(), ConstraintNorm()],
           st_constraints=[ConstraintNonneg()],
           tol_increase=1.0,
           tol_n_increase=10,
           tol_err_change=1e-14,
           tol_n_above_min=10):
    """Perform multivariate curve resolution (MCR) on the result on the
    decomposition. MCR is carried out using the PyMCR library, details of
    which can be found at the following link:

    https://github.com/hyperspy/hyperspy/pull/url

    If spatial simplicity is chosen, a varimax rotation is computed on the
    SVD loadings.  This rotation is applied to the factors, which are then
    fit to the input data via MCR until the convergence criteria are met.
    If spectral simplicity is chosen, the varimax rotation is calculated
    directly on the factors prior to MCR.

    In addition, prior to MCR fitting, the rotated factors are flipped if
    necessary so that they are mostly positive. This is required since a
    non-negativity constraint is applied.

    Parameters
    ----------
    number_of_components : int
        number of principal components to pass to the MCR algorithm
    simplicity : str
        Data is rotated to enforce simplicity in either the spatial or
        the spectral domains prior to MCR fitting.
    factors : Signal or numpy array.
        Factors to decompose. If None, the BSS is performed on the
        factors of a previous decomposition. If a Signal instance the
        navigation dimension must be 1 and the size greater than 1.
    comp_list : boolen numpy array
        choose the components to use by the boolean list. It permits
        to choose non contiguous components.
    mask : bool numpy array or Signal instance.
        If not None, the signal locations marked as True are masked. The
        mask shape must be equal to the signal shape
        (navigation shape) when `on_loadings` is False (True).
    compute : bool
        If the decomposition results are lazy, compute the BSS components
        so that they are not lazy.
        Default is False.
    verbosity : str
        One of ``['error', 'warning', 'info', 'debug']``
        Controls the verbosity of the external pyMCR routines. The
        strings provided correspond to levels of the ``logging`` module.
        Default is ``'error'`` (only critical failure output).
    c_regr : str, class
        Regression class (or string) for calculating the C matrix.
        Must be either 'OLS' or 'NNLS'. Default is 'OLS".
    st_regr : str
        Regression class (or string) for calculating the S^T matrix.
        Must be either 'OLS' or 'NNLS'. Default is 'OLS'.
    max_iter : int
        Maximum number of iterations. One iteration calculates both C and S^T.
        Default value is 100
    c_constraints : list
        List of constraints applied to calculation of C matrix
        Default is [ConstraintNonneg(), ConstraintNorm()]
    st_constraints : list
        List of constraints applied to calculation of S^T matrix
        Default is [ConstraintNonneg()]
    tol_increase : float
        Factor increase to allow in err attribute. Set to 0 for no increase
        allowed. E.g., setting to 1.0 means the err can double per iteration.
        Default is 1.0
    tol_n_increase : int
        Number of consecutive iterations for which the err attribute can
        increase
        Default is 10
    tol_err_change : float
        If err changes less than tol_err_change, per iteration, break.
        Default is 1e-14
    tol_n_above_min : int
        Number of half-iterations that can be performed without reaching a
        new error-minimum
        Default is 10
    """
    from hyperspy.signal import BaseSignal

    lr = self.learning_results
    data = self.data

    factors = self.get_decomposition_factors()
    loadings = self.get_decomposition_loadings()

    # Check factors
    if not isinstance(factors, BaseSignal):
        raise ValueError(
            "`factors` must be a BaseSignal instance, but an object of type "
            "%s was provided." %
            type(factors))

    # Check factor dimensions
    if factors.axes_manager.navigation_dimension != 1:
        raise ValueError("`factors` must have navigation dimension"
                         "equal one, but the navigation dimension "
                         "of the given factors is %i." %
                         factors.axes_manager.navigation_dimension
                         )
    elif factors.axes_manager.navigation_size < 2:
        raise ValueError("`factors` must have navigation size"
                         "greater than one, but the navigation "
                         "size of the given factors is %i." %
                         factors.axes_manager.navigation_size
                         )

    # Select components to fit
    if number_of_components is not None:
        comp_list = range(number_of_components)
    elif comp_list is not None:
        number_of_components = len(comp_list)
    else:
        if lr.output_dimension is not None:
            number_of_components = lr.output_dimension
            comp_list = range(number_of_components)
        else:
            raise ValueError(
                "No `number_of_components` or `comp_list` provided.")
    loadings = stack([loadings.inav[i] for i in comp_list])
    factors = stack([factors.inav[i] for i in comp_list])

    # Unfold in case the signal_dimension > 1
    factors.unfold()
    loadings.unfold()
    if mask is not None:
        mask.unfold()
        factors.data = factors.data.T[np.where(~mask.data)]
    else:
        factors.data = factors.data.T

    if self.learning_results.poissonian_noise_normalized is True:
        spec_weight_vec = self._root_bH.T.squeeze()
        im_weight_vec = self._root_aG.squeeze()
    else:
        spec_weight_vec = None
        im_weight_vec = None

    # Set logging level for pyMCR:
    levels = {'error': logging.ERROR,
              'warning': logging.WARNING,
              'info': logging.INFO,
              'debug': logging.DEBUG}
    logging.getLogger('pymcr.mcr').setLevel(levels[verbosity])

    # Perform MCR
    if simplicity == 'spatial':
        rot_loadings, rotation = orthomax(loadings.data.T, gamma=1)
        rot_loadings = np.array(rot_loadings)
        rotation = np.array(rotation)
        rot_factors = np.dot(factors.data, rotation)
        rot_factors = np.sign(rot_factors.sum(0)) * rot_factors

        rot_factors[rot_factors < 0] = 0
        if self.learning_results.poissonian_noise_normalized is True:
            rot_factors = (rot_factors.T / spec_weight_vec).T
            rot_factors = np.nan_to_num(rot_factors)
            data = (data.T / im_weight_vec).T / spec_weight_vec
            data = np.nan_to_num(data)

        fitmcr = McrAR(max_iter=max_iter,
                       st_regr=st_regr,
                       c_regr=c_regr,
                       c_constraints=c_constraints,
                       st_constraints=st_constraints,
                       tol_increase=tol_increase,
                       tol_n_increase=tol_n_increase,
                       tol_err_change=tol_err_change,
                       tol_n_above_min=tol_n_above_min)
        f = io.StringIO()
        with redirect_stdout(f):
            fitmcr.fit(data.T, C=rot_factors, verbose=False)
        _logger.info("PyMCR result: %s" % f.getvalue())

        if self.learning_results.poissonian_noise_normalized is True:
            loadings_out = (fitmcr.ST_opt_ * im_weight_vec).T
            factors_out = (fitmcr.C_opt_.T * spec_weight_vec).T
            data = (data.T * im_weight_vec).T / spec_weight_vec
        else:
            loadings_out = fitmcr.ST_opt_.T
            factors_out = fitmcr.C_opt_

    elif simplicity == 'spectral':
        rot_factors, rotation = orthomax(factors.data, gamma=1)
        rot_factors = np.array(rot_factors)
        rotation = np.array(rotation)
        rot_factors = np.sign(rot_factors.sum(0)) * rot_factors
        rot_factors[rot_factors < 0] = 0
        if self.learning_results.poissonian_noise_normalized is True:
            rot_factors = (rot_factors.T / spec_weight_vec).T
            rot_factors = np.nan_to_num(rot_factors)
            data = (data.T / im_weight_vec).T / spec_weight_vec
            data = np.nan_to_num(data)

        fitmcr = McrAR(max_iter=max_iter,
                       st_regr=st_regr,
                       c_regr=c_regr,
                       c_constraints=c_constraints,
                       st_constraints=st_constraints,
                       tol_increase=tol_increase,
                       tol_n_increase=tol_n_increase,
                       tol_err_change=tol_err_change,
                       tol_n_above_min=tol_n_above_min)
        f = io.StringIO()
        with redirect_stdout(f):
            fitmcr.fit(data, ST=rot_factors.T, verbose=False)
        _logger.info("PyMCR result: %s" % f.getvalue())

        if self.learning_results.poissonian_noise_normalized is True:
            loadings_out = (fitmcr.C_opt_.T * im_weight_vec).T
            factors_out = (fitmcr.ST_opt_ * spec_weight_vec).T
            data = (data.T * im_weight_vec).T / spec_weight_vec
        else:
            loadings_out = fitmcr.C_opt_
            factors_out = fitmcr.ST_opt_.T

    else:
        raise ValueError("'simplicity' must be either 'spatial' or"
                         "'spectral'."
                         "{} was provided.".format(str(simplicity)))

    factors_out = factors_out/factors_out.sum(0)
    loadings_out = loadings_out/loadings_out.sum(0)

    return factors_out, loadings_out
