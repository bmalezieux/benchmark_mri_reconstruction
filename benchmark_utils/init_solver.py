
import numpy as np
from modopt.opt.algorithms import POGM, ForwardBackward, Condat
from modopt.opt.linear import Identity
from mri.operators.gradient.gradient import GradAnalysis, GradSynthesis

OPTIMIZERS = {"pogm": "synthesis", "fista": "analysis", "condat-vu": "analysis", None: None}

def get_grad_op(fourier_op, grad_formulation, linear_op=None, verbose=False, **kwargs):
    """Create gradient operator specific to the problem."""
    if grad_formulation == "analysis":
        return GradAnalysis(fourier_op=fourier_op, verbose=verbose, **kwargs)
    if grad_formulation == "synthesis":
        return GradSynthesis(
            linear_op=linear_op,
            fourier_op=fourier_op,
            verbose=verbose,
            **kwargs,
            )

def initialize_opt(
    opt_name,
    grad_op,
    linear_op,
    prox_op,
    x_init=None,
    synthesis_init=False,
    opt_kwargs=None,
    metric_kwargs=None,
):
    """
    Initialize an Optimizer with the suitable parameters.

    Parameters:
    ----------
    grad_op: OperatorBase
        Gradient Operator for the data consistency
    x_init: ndarray, default None
        Initial value for the reconstruction. If None use a zero Array.
    synthesis_init: bool, default False
        Is the initial_value in the image space of the space_linear operator ?
    opt_kwargs: dict, default None
        Extra kwargs for the initialisation of Optimizer
    metric_kwargs: dict, default None
        Extra kwargs for the metric api of ModOpt

    Returns:
    -------
    An Optimizer Instance to perform the reconstruction with.
    See Also:
    --------
    Modopt.opt.algorithms

    """
    if x_init is None:
        x_init = np.squeeze(
            np.zeros(
                (grad_op.fourier_op.n_coils, *grad_op.fourier_op.shape),
                dtype="complex64",
            )
        )

    if not synthesis_init and hasattr(grad_op, "linear_op"):
        alpha_init = grad_op.linear_op.op(x_init)
    elif synthesis_init and not hasattr(grad_op, "linear_op"):
        x_init = linear_op.adj_op(x_init)
    elif not synthesis_init and hasattr(grad_op, "linear_op"):
        alpha_init = x_init
    opt_kwargs = opt_kwargs or dict()
    metric_kwargs = metric_kwargs or dict()

    beta = grad_op.inv_spec_rad
    if opt_name == "pogm":
        opt = POGM(
            u=alpha_init,
            x=alpha_init,
            y=alpha_init,
            z=alpha_init,
            grad=grad_op,
            prox=prox_op,
            linear=linear_op,
            beta_param=beta,
            sigma_bar=opt_kwargs.pop("sigma_bar", 0.96),
            auto_iterate=opt_kwargs.pop("auto_iterate", False),
            **opt_kwargs,
            **metric_kwargs,
        )
    elif opt_name == "fista":
        opt = ForwardBackward(
            x=x_init,
            grad=grad_op,
            prox=prox_op,
            linear=linear_op,
            beta_param=beta,
            lambda_param=opt_kwargs.pop("lambda_param", 1.0),
            auto_iterate=opt_kwargs.pop("auto_iterate", False),
            **opt_kwargs,
            **metric_kwargs,
        )
    elif opt_name == "condat-vu":

        y_init = linear_op.op(x_init)

        opt = Condat(
            x=x_init,
            y=y_init,
            grad=grad_op,
            prox=Identity(),
            prox_dual= prox_op,
            linear=linear_op,
            **opt_kwargs,
            **metric_kwargs,
        )

    else:
        raise ValueError(f"Optimizer {opt_name} not implemented")
    return opt
