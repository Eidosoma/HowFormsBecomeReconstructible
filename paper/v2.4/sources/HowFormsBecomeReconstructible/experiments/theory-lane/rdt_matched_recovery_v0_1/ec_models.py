"""Fixed ordinary features and convex logistic corrections with a known offset."""
import math
import numpy as np
from scipy.special import expit

FAMILIES = ("boundary0", "direct8", "direct64", "successor64")
HEADS = ("mean", "scale", "expression")


def require(ok, message):
    if not ok:
        raise ValueError(message)


def base_feature(row, name):
    curve, family = name.split("_", 1)
    require(curve in ("linear", "quadratic") and family in ("condition0", *FAMILIES), "Unknown base model")
    require(row["regime"] in ("matched", "independent"), "Unknown noise")
    d, n = (row["injury"] - 24) / 12, float(row["regime"] == "independent")
    result = [d, n, d*n]
    if family != "condition0":
        require(len(row["boundary"]) == 11, "B11 required")
        result = [*row["boundary"], *result]
    if family in ("direct8", "direct64", "successor64"):
        q = row["fractions"]["successor32" if family == "successor64" else family]
        require(0 <= q <= 1, "Invalid assay fraction")
        result += [q, d*q, n*q]
    if curve == "quadratic":
        result += [d*d, n*d*d]
    require(np.isfinite(result).all(), "Nonfinite features")
    return result


def correction_feature(row, ell, head):
    require(head in HEADS and row["regime"] in ("matched", "independent"), "Unknown correction")
    require(row["current_pass"] in (0, 1) and math.isfinite(ell), "Invalid expression/logit")
    d, n, s = (row["injury"] - 24) / 12, float(row["regime"] == "independent"), 2*row["current_pass"]-1
    result = [d, n, d*n, d*d, n*d*d]
    if head in ("scale", "expression"):
        result += [ell, d*ell, n*ell, d*n*ell]
    if head == "expression":
        result += [s, d*s, n*s, d*n*s]
    require(np.isfinite(result).all(), "Nonfinite correction features")
    return result


def logit(x, model):
    x = np.asarray(x, float)
    mean, scale, theta = (np.asarray(model[k], float) for k in ("mean", "scale", "coefficients"))
    require(x.ndim == 2 and x.shape[1] == len(mean) == len(scale) == len(theta)-1, "Model dimensions")
    require(np.isfinite(x).all() and np.isfinite(theta).all() and np.all(scale > 0), "Invalid model")
    z = np.column_stack((np.ones(len(x)), (x-mean)/scale))
    eta = z @ theta
    for row, value in zip(z, eta, strict=True):
        scalar = math.fsum(float(a)*float(b) for a, b in zip(row, theta, strict=True))
        require(abs(float(expit(scalar))-float(expit(value))) < 1e-12, "Scalar probability differs")
    require(np.isfinite(eta).all(), "Nonfinite logit")
    return eta


def objective(theta, z, y, w, offset):
    eta = offset + z @ theta
    p = expit(eta)
    value = w @ (np.logaddexp(0, eta)-y*eta) + .005*(theta[1:] @ theta[1:])
    gradient = z.T @ (w*(p-y))
    gradient[1:] += .01*theta[1:]
    hessian = z.T @ ((w*p*(1-p))[:, None]*z)
    hessian[1:, 1:] += .01*np.eye(z.shape[1]-1)
    return float(value), gradient, hessian


def arrays(x, y, weights, offset):
    x, y, w, offset = map(lambda a: np.asarray(a, float), (x, y, weights, offset))
    require(x.ndim == 2 and y.ndim == w.ndim == offset.ndim == 1 and len(x) == len(y) == len(w) == len(offset) > 0,
            "Invalid training shapes")
    require(np.isfinite(x).all() and np.isfinite(offset).all() and np.isfinite(w).all() and
            np.all(w > 0) and np.isin(y, [0, 1]).all() and 0 < y.mean() < 1, "Invalid training data")
    return x, y, w/w.sum(), offset


def fit(x, y, weights, offset):
    x, y, w, offset = arrays(x, y, weights, offset)
    mean = w @ x
    scale = np.sqrt(w @ ((x-mean)**2))
    scale[scale < 1e-12] = 1.
    z = np.column_stack((np.ones(len(x)), (x-mean)/scale))
    theta = np.zeros(z.shape[1])
    for iteration in range(100):
        value, gradient, hessian = objective(theta, z, y, w, offset)
        if np.max(abs(gradient)) <= 1e-8:
            break
        direction = np.linalg.solve(hessian, gradient)
        descent = float(gradient @ direction)
        require(descent > 0 and np.isfinite(direction).all(), "Invalid Newton direction")
        step = 1.
        for _ in range(40):
            trial = theta-step*direction
            loss, _, _ = objective(trial, z, y, w, offset)
            tolerance = 8*np.finfo(float).eps*max(1., abs(value))
            if loss <= value-1e-4*step*descent+tolerance:
                theta = trial
                break
            step /= 2
        else:
            raise ArithmeticError("Correction line search failed; no retry")
    else:
        raise ArithmeticError("Correction iteration ceiling; no retry")
    value, gradient, _ = objective(theta, z, y, w, offset)
    require(np.max(abs(gradient)) <= 1e-8, "Unqualified correction fit")
    model = dict(mean=mean.tolist(), scale=scale.tolist(), coefficients=theta.tolist(), loss=value,
                 gradient_max=float(np.max(abs(gradient))), iterations=iteration, ridge=.01,
                 optimizer="Damped Newton with fixed logit offset; gradient ceiling1e-8")
    audit_fit(x, y, w, offset, model)
    return model


def audit_fit(x, y, weights, offset, model):
    x, y, w, offset = arrays(x, y, weights, offset)
    z = np.column_stack((np.ones(len(x)), (x-model["mean"])/model["scale"]))
    theta = np.asarray(model["coefficients"])
    scalar_eta = np.array([float(o)+math.fsum(float(a)*float(b) for a,b in zip(row,theta,strict=True))
                           for o,row in zip(offset,z,strict=True)])
    p = np.array([1/(1+math.exp(-v)) if v >= 0 else math.exp(v)/(1+math.exp(v)) for v in scalar_eta])
    gradient = [math.fsum(float(wi)*float(pi-yi)*float(zi) for wi,pi,yi,zi in zip(w,p,y,z[:,j],strict=True))
                + (.01*float(theta[j]) if j else 0.) for j in range(len(theta))]
    loss = math.fsum(float(wi)*(max(float(eta),0.)+math.log1p(math.exp(-abs(float(eta))))-float(yi)*float(eta))
                     for wi,eta,yi in zip(w,scalar_eta,y,strict=True)) + .005*math.fsum(float(t)**2 for t in theta[1:])
    hessian = z.T @ ((w*p*(1-p))[:,None]*z)
    hessian[1:,1:] += .01*np.eye(len(theta)-1)
    minimum = float(np.linalg.eigvalsh(hessian).min())
    require(max(map(abs, gradient)) <= 1e-8 and abs(loss-model["loss"]) < 1e-12 and minimum > 0,
            "Independent fit verification failed")
    return dict(gradient_max=max(map(abs,gradient)), loss_residual=abs(loss-model["loss"]),
                minimum_hessian_eigenvalue=minimum)


def raw_parameters(model):
    coefficient = np.asarray(model["coefficients"][1:]) / np.asarray(model["scale"])
    intercept = model["coefficients"][0] - coefficient @ model["mean"]
    return float(intercept), coefficient


def correction_functions(model, head, injury, regime):
    d, n = (injury-24)/12, float(regime == "independent")
    a0, coefficient = raw_parameters(model)
    a = a0 + coefficient[:5] @ np.array([d,n,d*n,d*d,n*d*d])
    b = coefficient[5:9] @ np.array([1,d,n,d*n]) if head != "mean" else 0.
    c = coefficient[9:13] @ np.array([1,d,n,d*n]) if head == "expression" else 0.
    return dict(A=float(a), B=float(b), C=float(c), effective_logit_slope=float(1+b))
