import logging
import numpy as np
from pypesto import Result
from ..optimize import OptimizerResult, OptimizeOptions, minimize
from .profiler import ProfilerResult
from .profile_startpoint import fixed_step


logger = logging.getLogger(__name__)


class ProfileOptions(dict):
    """
    Options for optimization based profiling.

    Parameters
    ----------

    next_profile_startpoint: function handle, optional
        function which creates the next startpoint for optimization of the profile from the profile history
    """

    def __init__(self):
        super().__init__()
        self.default_step_size = 0.01

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key)

    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

    @staticmethod
    def assert_instance(maybe_options):
        """
        Returns a valid options object.

        Parameters
        ----------

        maybe_options: OptimizeOptions or dict
        """
        if isinstance(maybe_options, ProfileOptions):
            return maybe_options
        options = ProfileOptions(**maybe_options)
        return options


def profile(
        problem,
        result,
        optimizer,
        profile_index=None,
        result_index=1,
        create_profile_startpoint=None,
        profile_options=None,
        optimize_options=None) -> Result:
    """
    This is the main function to call to do parameter profiling.

    Parameters
    ----------

    problem: pypesto.Problem
        The problem to be solved.

    result: pypesto.Result
        A result object to initialize profiling and to append the profiling
        results to. For example, one might append more profiling runs to a
        previous profile, in order to merge these.
        The existence of an optimization result is obligatory.

    optimizer: pypesto.Optimizer
        The optimizer to be used along each profile.

    profile_index: integer array, optional
        array with parameter indices, whether a profile should
        be computed (1) or not (0)

    result_index: integer, optional
        index, from which optimization result profiling should be started
        (default: global optimum, i.e., index = 1)

    create_profile_startpoint: callable, optional
        Method for how to create the next start point for profile optimization.

    profile_options: pypesto.ProfileOptions, optional
        Various options applied to the profile optimization.

    optimize_options: pypesto.OptimizeOptions, optional
        Various options applied to the optimizer.
    """

    # profiling indices
    if profile_index is None:
        profile_index = np.ones(problem.dim_full)

    # profile startpoint method
    if create_profile_startpoint is None:
        def create_profile_startpoint(x, par_index, par_direction):
            return fixed_step(x, par_index, par_direction, step_size = profile_options.default_step_size)

    # check profiling options
    if profile_options is None:
        profile_options = ProfileOptions()
    profile_options = ProfileOptions.assert_instance(profile_options)

    # check optimization ptions
    if optimize_options is None:
        optimize_options = OptimizeOptions()
    optimize_options = OptimizeOptions.assert_instance(optimize_options)

    # assign startpoints
    initialize_profile(problem, result, result_index)

    # loop over parameters for profiling
    for i_parameter in range(0, problem.dim_full):
        if profile_index[i_parameter] == 0:
            continue

        current_profile = result.profile_result.get_current_profile(i_parameter)

        # compute profile in descending and ascending direction
        for par_direction in [-1,1]:

            # get current position on the profile path
            x_now = current_profile.x_path[-1,:]

            # compute the new start point for optimization
            x_next =  create_profile_startpoint(x_now, i_parameter, par_direction)

        try:
            optimizer_result = optimizer.minimize(problem, startpoint, j_start)
        except Exception as err:
            if options.allow_failed_starts:
                optimizer_result = handle_exception(
                    problem.objective, startpoint, j_start, err)
            else:
                raise

        # append to result
        result.optimize_result.append(profile_result)

    # sort by best fval
    result.optimize_result.sort()

    return result


def initialize_profile(
        problem,
        result,
        result_index):
    """
       This is function initializes profiling based on a previous optimization.

       Parameters
       ----------

       problem: pypesto.Problem
           The problem to be solved.

       result: pypesto.Result
           A result object to initialize profiling and to append the profiling
           results to. For example, one might append more profiling runs to a
           previous profile, in order to merge these.
           The existence of an optimization result is obligatory.

       result_index: integer
           The index, starting from which optimization result profiling
           should be carried out
       """
    if result.optimize_result is None:
        print("Optimization has to be carried before profiling can be done.")
        return None

    for iParameter in range(0, problem.dim_full):
        tmp_optimize_result = result.optimize_result.as_list()
        result.profile_result.append_profile(ProfilerResult(tmp_optimize_result[result_index]["x"],
                                                            tmp_optimize_result[result_index]["fval"],
                                                            np.array([1]),
                                                            np.linalg.norm(tmp_optimize_result[result_index]["grad"]),
                                                            tmp_optimize_result[result_index]["exitflag"],
                                                            np.array([0]),
                                                            np.array([0]),
                                                            np.array([0]),
                                                            np.array([0]),
                                                            np.array([0]),
                                                            None))
