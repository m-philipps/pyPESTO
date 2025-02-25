"""Utility functions for :py:func:`pypesto.optimize.minimize`."""

import logging
import os
from pathlib import Path
from typing import Iterable, List

import h5py

from ..C import PYPESTO_MAX_N_STARTS
from ..engine import Engine, SingleCoreEngine
from ..objective import HistoryOptions
from ..result import Result
from ..store.save_to_hdf5 import get_or_create_group
from .optimizer import OptimizerResult

logger = logging.getLogger(__name__)


def preprocess_hdf5_history(
    history_options: HistoryOptions,
    engine: Engine,
):
    """Create a folder for partial HDF5 files if parallelization is used.

    This is because single hdf5 file access is not thread-safe.

    Parameters
    ----------
    engine:
        The Engine which is used in the optimization.
    history_options:
        The HistoryOptions used in the optimization.

    Returns
    -------
    history_requires_postprocessing:
        Whether history storage post-processing is required.
    """
    storage_file = history_options.storage_file

    # nothing to do if no history stored
    if storage_file is None:
        return False

    # extract storage type
    path = Path(storage_file)

    # nothing to do if csv history and correctly set
    if path.suffix == ".csv":
        if "{id}" not in storage_file:
            raise ValueError(
                "For csv history, the `storage_file` must contain an `{id}` "
                "template"
            )
        return False

    # assuming hdf5 history henceforth
    if path.suffix not in [".h5", ".hdf5"]:
        raise ValueError(
            "Only history storage to '.csv' and '.hdf5' is supported, got "
            f"{path.suffix}",
        )

    # nothing to do if no parallelization
    if isinstance(engine, SingleCoreEngine):
        return False

    # create directory with same name as original file stem
    template_path = (
        path.parent / path.stem / (path.stem + "_{id}" + path.suffix)
    )
    template_path.parent.mkdir(parents=True, exist_ok=True)
    # set history file to template path
    history_options.storage_file = str(template_path)

    return True


def postprocess_hdf5_history(
    ret: List[OptimizerResult],
    storage_file: str,
    history_options: HistoryOptions,
) -> None:
    """Create single history file pointing to files of multiple starts.

    Create links in `storage_file` to the history of each start contained in
    `ret`, the results of the optimization.

    Parameters
    ----------
    ret:
        The result iterable returned by the optimization.
    storage_file:
        The filename of the hdf5 file in which the histories
        are to be gathered.
    history_options:
        History options used in the optimization.
    """
    # create hdf5 file that gathers the others within history group
    with h5py.File(storage_file, mode='w') as f:
        # create file and group
        get_or_create_group(f, "history")
        # append links to each single result file
        for result in ret:
            id = result['id']
            f[f'history/{id}'] = h5py.ExternalLink(
                result['history'].file, f'history/{id}'
            )

    # reset storage file (undo preprocessing changes)
    history_options.storage_file = storage_file


def bound_n_starts_from_env(n_starts: int):
    """Bound number of optimization starts from environment variable.

    Uses environment variable `PYPESTO_MAX_N_STARTS`.
    This is used to speed up testing, while in application it should not
    be used.

    Parameters
    ----------
    n_starts: Number of starts desired.

    Returns
    -------
    n_starts_new:
        The original number of starts, or the minimum with the environment
        variable, if exists.
    """
    if PYPESTO_MAX_N_STARTS not in os.environ:
        return n_starts
    n_starts_new = min(n_starts, int(os.environ[PYPESTO_MAX_N_STARTS]))

    logger.info(
        f"Bounding number of samples from {n_starts} to {n_starts_new} via "
        f"environment variable {PYPESTO_MAX_N_STARTS}"
    )

    return n_starts_new


def assign_ids(
    n_starts: int,
    ids: Iterable[str] = None,
    result: Result = None,
) -> Iterable[str]:
    """
    Assign ids to starts.

    ids:
        Ids assigned to the startpoints.
    result:
        A result object to append the optimization results to. For example,
        one might append more runs to a previous optimization. Assign only
        unique ids.
    n_starts:
        Number of starts of the optimizer.
    """
    used_ids = set()
    if result is not None:
        used_ids = set(result.optimize_result.id)
        N_used = len(used_ids)
    if ids is None:
        i = 0
        ids = [str(j) for j in range(i * n_starts, (i + 1) * n_starts)]
        while not used_ids.isdisjoint(ids):
            i += 1
            ids = [
                str(j) for j in range(N_used * i, N_used * (i + 1) + n_starts)
            ]
    if len(ids) != n_starts:
        raise AssertionError("Number of starts and ids must coincide.")
    if not used_ids.isdisjoint(ids):
        raise AssertionError(
            "Manually assigned ids must differ from existing ones."
        )
    return ids
