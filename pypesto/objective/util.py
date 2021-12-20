import numpy as np
from typing import Union, Tuple
from .constants import MODE_FUN, MODE_RES, FVAL, GRAD, HESS, RES, SRES


def _check_none(fun):
    """Return None if any input argument is None; Wrapper function."""
    def checked_fun(*args, **kwargs):
        if any(x is None for x in [*args, *(kwargs.values())]):
            return None
        return fun(*args, **kwargs)
    return checked_fun


@_check_none
def res_to_chi2(res: np.ndarray) -> Union[float, None]:
    """Translate residuals to chi2 values, `chi2 = sum(res**2)`."""
    return np.dot(res, res)


@_check_none
def chi2_to_fval(chi2: float) -> Union[float, None]:
    """Translate chi2 to function value, `fval = 0.5*chi2 = 0.5*sum(res**2)`.

    Note that for the function value we thus employ a probabilistic
    interpretation, as the log-likelihood of a standard normal noise model.
    This is in line with e.g. AMICI's and SciPy's objective definition.
    """
    return 0.5 * chi2


@_check_none
def res_to_fval(res: np.ndarray) -> Union[float, None]:
    """Translate residuals to function value, `fval = 0.5*sum(res**2)`."""
    return chi2_to_fval(res_to_chi2(res))


@_check_none
def sres_to_schi2(res: np.ndarray, sres: np.ndarray):
    """Translate residual sensitivities to chi2 gradient."""
    return 2 * res.dot(sres)


@_check_none
def schi2_to_grad(schi2: np.ndarray) -> np.ndarray:
    """Translate chi2 gradient to function value gradient.

    See also :func:`chi2_to_fval`.
    """
    return 0.5 * schi2


@_check_none
def sres_to_grad(res: np.ndarray, sres: np.ndarray):
    """Translate residual sensitivities to function value gradient.

    Assumes `fval = 0.5*sum(res**2)`.

    See also :func:`chi2_to_fval`.
    """
    return schi2_to_grad(sres_to_schi2(res, sres))


@_check_none
def sres_to_fim(sres: np.ndarray):
    """Translate residual sensitivities to FIM.

    The FIM is based on the function values, not chi2, i.e. has a normalization
    of 0.5 as in :func:`res_to_fval`.
    """
    return sres.transpose().dot(sres)


def get_zero_result_dict(
        x: np.ndarray,
        sensi_orders: Tuple[int, ...] = (0, ),
        mode: str = MODE_FUN):
    """Return an result object for the trivial = constant objective.

    This is used as the dummy part for get_negloglikelihood and
    get_neglogprior, if the objective does not contain a likelihood/prior
    contribution.

    :param x:
    :param sensi_orders:
    :param mode:
    :return:
    """
    result = {}

    if mode == MODE_FUN:
        if 0 in sensi_orders:
            result[FVAL] = 0
        if 1 in sensi_orders:
            result[GRAD] = np.zeros_like(x)
        if 2 in sensi_orders:
            result[HESS] = np.zeros((len(x), len(x)))
    elif mode == MODE_RES:
        if 0 in sensi_orders:
            result[RES] = np.array([0])
        if 1 in sensi_orders:
            result[SRES] = np.zeros((1, len(x)))
        if 2 in sensi_orders:
            raise ValueError(f"Sensitivity order 2 are not supported "
                             f"for {MODE_RES}.")
    else:
        raise ValueError(f'unknown mode {mode}.')

    return result
