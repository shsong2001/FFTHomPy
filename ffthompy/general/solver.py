#!/usr/bin/python
import numpy as np
from ffthompy.general.base import Timer
from ffthompy.matvec import VecTri


def linear_solver(Afun=None, ATfun=None, B=None, x0=None, par=None,
                  solver=None, callback=None):
    """
    Wraper for various linear solvers suited for FFT-based homogenization.
    """
    tim = Timer('Solving linsys by %s' % solver)
    if callback is not None:
        callback(x0)

    if solver.lower() in ['cg']: # conjugate gradients
        x, info = CG(Afun, B, x0=x0, par=par, callback=callback)
    elif solver.lower() in ['bicg']: # biconjugate gradients
        x, info = BiCG(Afun, ATfun, B, x0=x0, par=par, callback=callback)
    elif solver.lower() in ['iterative']: # iterative solver
        x, info = richardson(Afun, B, x0, par=par, callback=callback)
    elif solver.lower() in ['chebyshev', 'cheby']: # iterative solver
        x, info = cheby2TERM(A=Afun, B=B, x0=x0, par=par, callback=callback)
    elif solver.split('_')[0].lower() in ['scipy']: # solvers in scipy
        from scipy.sparse.linalg import LinearOperator, cg, bicg
        if solver == 'scipy_cg':
            Afun.define_operand(B)
            Afunvec = LinearOperator(Afun.shape, matvec=Afun.matvec,
                                     dtype=np.float64)
            xcol, info = cg(Afunvec, B.vec(), x0=x0.vec(),
                            tol=par['tol'],
                            maxiter=par['maxiter'],
                            M=None, callback=callback)
            info = {'info': info}
        elif solver == 'scipy_bicg':
            Afun.define_operand(B)
            ATfun.define_operand(B)
            Afunvec = LinearOperator(Afun.shape, matvec=Afun.matvec,
                                     rmatvec=ATfun.matvec, dtype=np.float64)
            xcol, info = bicg(Afunvec, B.vec(), x0=x0.vec(),
                              tol=par['tol'],
                              maxiter=par['maxiter'],
                              M=None, callback=callback)
        res = dict()
        res['info'] = info
        x = VecTri(val=np.reshape(xcol, B.dN()))
    else:
        msg = "This kind (%s) of linear solver is not implemented" % solver
        raise NotImplementedError(msg)
    tim.measure(print_time=False)
    info.update({'time': tim.vals})
    return x, info


def richardson(Afun, B, x0, par=None, callback=None):
    omega = 1./par['alpha']
    res = {'norm_res': 1.,
           'kit': 0}
    x = x0
    while (res['norm_res'] > par['tol'] and res['kit'] < par['maxiter']):
        res['kit'] += 1
        x_prev = x
        x = x - omega*(Afun*x - B)
        dif = x_prev-x
        res['norm_res'] = float(dif.T*dif)**0.5
        if callback is not None:
            callback(x)
    return x, res


def CG(Afun, B, x0=None, par=None, callback=None):
    """
    Conjugate gradients solver.

    Parameters
    ----------
    Afun : Matrix, LinOper, or numpy.array of shape (n, n)
        it stores the matrix data of linear system and provides a matrix by
        vector multiplication
    B : VecTri or numpy.array of shape (n,)
        it stores a right-hand side of linear system
    x0 : VecTri or numpy.array of shape (n,)
        initial approximation of solution of linear system
    par : dict
        parameters of the method
    callback :

    Returns
    -------
    x : VecTri or numpy.array of shape (n,)
        resulting unknown vector
    res : dict
        results
    """
    if x0 is None:
        x0 = B
    if par is None:
        par = dict()
    if 'tol' not in list(par.keys()):
        par['tol'] = 1e-6
    if 'maxiter' not in list(par.keys()):
        par['maxiter'] = int(1e3)

    res = dict()
    xCG = x0
    Ax = Afun*x0
    R = B - Ax
    P = R
    rr = float(R.T*R)
    res['kit'] = 0
    res['norm_res'] = np.double(rr)**0.5 # /np.norm(E_N)
    norm_res_log = []
    norm_res_log.append(res['norm_res'])
    while (res['norm_res'] > par['tol']) and (res['kit'] < par['maxiter']):
        res['kit'] += 1 # number of iterations
        AP = Afun*P
        alp = float(rr/(P.T*AP))
        xCG = xCG + alp*P
        R = R - alp*AP
        rrnext = float(R.T*R)
        bet = rrnext/rr
        rr = rrnext
        P = R + bet*P
        res['norm_res'] = np.double(rr)**0.5
        norm_res_log.append(res['norm_res'])
        if callback is not None:
            callback(xCG)
    if res['kit'] == 0:
        res['norm_res'] = 0
    return xCG, res


def BiCG(Afun, ATfun, B, x0=None, par=None, callback=None):
    """
    BiConjugate gradient solver.

    Parameters
    ----------
    Afun : Matrix, LinOper, or numpy.array of shape (n, n)
        it stores the matrix data of linear system and provides a matrix by
        vector multiplication
    B : VecTri or numpy.array of shape (n,)
        it stores a right-hand side of linear system
    x0 : VecTri or numpy.array of shape (n,)
        initial approximation of solution of linear system
    par : dict
        parameters of the method
    callback :

    Returns
    -------
    x : VecTri or numpy.array of shape (n,)
        resulting unknown vector
    res : dict
        results
    """
    if x0 is None:
        x0 = B
    if par is None:
        par = dict()
    if 'tol' not in par:
        par['tol'] = 1e-6
    if 'maxiter' not in par:
        par['maxiter'] = 1e3

    res = dict()
    res['time'] = dbg.start_time()
    xBiCG = x0
    Ax = Afun*x0
    R = B - Ax
    Rs = R
    rr = float(R.T*Rs)
    P = R
    Ps = Rs
    res['kit'] = 0
    res['norm_res'] = rr**0.5 # /np.norm(E_N)
    norm_res_log = []
    norm_res_log.append(res['norm_res'])
    while (res['norm_res'] > par['tol']) and (res['kit'] < par['maxiter']):
        res['kit'] += 1 # number of iterations
        AP = Afun*P
        alp = rr/float(AP.T*Ps)
        xBiCG = xBiCG + alp*P
        R = R - alp*AP
        Rs = Rs - alp*ATfun*Ps
        rrnext = float(R.T*Rs)
        bet = rrnext/rr
        rr = rrnext
        P = R + bet*P
        Ps = Rs + bet*Ps
        res['norm_res'] = rr**0.5
        norm_res_log.append(res['norm_res'])
        if callback is not None:
            callback(xBiCG)
    res['time'] = dbg.get_time(res['time'])
    if res['kit'] == 0:
        res['norm_res'] = 0
    return xBiCG, res

def cheby2TERM(A, B, x0, M=None, par=None, callback=None):
    """
    Chebyshev two-term iterative solver

    Parameters
    ----------
    Afun : Matrix, LinOper, or numpy.array of shape (n, n)
        it stores the matrix data of linear system and provides a matrix by
        vector multiplication
    B : VecTri or numpy.array of shape (n,)
        it stores a right-hand side of linear system
    x0 : VecTri or numpy.array of shape (n,)
        initial approximation of solution of linear system
    par : dict
        parameters of the method
    callback :

    Returns
    -------
    x : VecTri or numpy.array of shape (n,)
        resulting unknown vector
    res : dict
        results
    """
    if par is None:
        par = dict()
    if 'tol' not in par:
        par['tol'] = 1e-06
    if 'maxit' not in par:
        par['maxit'] = 1e7
    if 'eigrange' not in par:
        raise NotImplementedError("It is necessary to calculate eigenvalues.")
    else:
        Egv = par['eigrange']

    res = dict()
    res['kit'] = 0
    bnrm2 = (B*B)**0.5
    Ib = 1.0/bnrm2
    if bnrm2 == 0:
        bnrm2 = 1.0
    x = x0
    r = B - A(x)
    r0 = np.double(r*r)**0.5
    res['norm_res'] = Ib*r0 # For Normal Residue
    if res['norm_res'] < par['tol']: # if errnorm is less than tol
        return x, res

    d = (Egv[1]+Egv[0])/2.0 # np.mean(par['eigrange'])
    c = (Egv[1]-Egv[0])/2.0 # par['eigrange'][1] - d
    v = 0*x0
    while (res['norm_res'] > par['tol']) and (res['kit'] < par['maxit']):
        res['kit'] += 1
        x_prev = x
        if res['kit'] == 1:
            p = 0
            w = 1/d
        elif res['kit'] == 2:
            p = -(1/2)*(c/d)*(c/d)
            w = 1/(d-c*c/2/d)
        else:
            p = -(c*c/4)*w*w
            w = 1/(d-c*c*w/4)
        v = r - p*v
        x = x_prev + w*v
        r = B - A(x)

        res['norm_res'] = (1.0/r0)*r.norm()

        if callback is not None:
            callback(x)

    if par['tol'] < res['norm_res']: # if tolerance is less than error norm
        print("Chebyshev solver does not converges!")
    else:
        print("Chebyshev solver converges.")

    if res['kit'] == 0:
        res['norm_res'] = 0
    return x, res
if __name__ == '__main__':
    exec(compile(open('../main_test.py').read(), '../main_test.py', 'exec'))
