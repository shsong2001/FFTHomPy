import numpy as np
import homogenize.projections as proj
from general.solver import linear_solver
from general.solver_pp import CallBack, CallBack_GA
from homogenize.matvec import (VecTri, Matrix, DFT, LinOper)
from homogenize.materials import Material


def homogenize_scalar(problem):
    """
    Homogenization of scalar elliptic problem.

    Parameters
    ----------
    problem : object
    """
    print ' '
    pb = problem
    print pb

    # Fourier projections
    _, hG1, hG2 = proj.get_Fourier_projections(pb.solve['N'], pb.Y,
                                               centered=True, NyqNul=True)
    hG1N = Matrix(name='hG1', val=hG1, Fourier=True)
    hG2N = Matrix(name='hG1', val=hG2, Fourier=True)

    if pb.solve['kind'] is 'GaNi':
        Nbar = pb.solve['N']
    elif pb.solve['kind'] is 'Ga':
        Nbar = 2*pb.solve['N'] - 1
        hG1N = hG1N.resize(Nbar)
        hG2N = hG2N.resize(Nbar)

    FN = DFT(name='FN', inverse=False, N=Nbar)
    FiN = DFT(name='FiN', inverse=True, N=Nbar)

    G1N = LinOper(name='G1', mat=[[FiN, hG1N, FN]])
    G2N = LinOper(name='G2', mat=[[FiN, hG2N, FN]])

    for primaldual in pb.solve['primaldual']:
        print '\nproblem: ' + primaldual
        solutions = np.zeros(pb.shape).tolist()
        results = np.zeros(pb.shape).tolist()

        # material coefficients
        mat = Material(pb)

        if pb.solve['kind'] is 'GaNi':
            A = mat.get_A_GaNi(pb.solve['N'], primaldual)
        elif pb.solve['kind'] is 'Ga':
            if 'M' in pb.solve:
                M = pb.solve['M']
            else:
                M = None
            A = mat.get_A_Ga(Nbar=Nbar, order=pb.solve['order'], M=M,
                             primaldual=primaldual)

        if primaldual is 'primal':
            GN = G1N
        else:
            GN = G2N

        Afun = LinOper(name='FiGFA', mat=[[GN, A]])

        for iL in np.arange(pb.dim): # iteration over unitary loads
            E = np.zeros(pb.dim)
            E[iL] = 1
            print 'macroscopic load E = ' + str(E)
            EN = VecTri(name='EN', macroval=E, N=Nbar)
            x_start = VecTri(N=Nbar)

            B = Afun(-EN) # RHS

            if not hasattr(pb.solver, 'callback'):
                cb = CallBack(A=Afun, B=B)
            elif pb.solver['callback'] == 'detailed':
                cb = CallBack_GA(A=Afun, B=B, EN=EN, A_Ga=A, GN=GN)
            else:
                raise NotImplementedError("The solver callback (%s) is not \
                    implemented" % (pb.solver['callback']))

            print 'solver : %s' % pb.solver['kind']
            cb(x_start) # initial callback
            X, info = linear_solver(solver=pb.solver['kind'], Afun=Afun, B=B,
                                    par=pb.solver, callback=cb)

            solutions[iL] = add_macro2minimizer(X, E)
            results[iL] = {'cb': cb, 'info': info}
            print cb

        # POSTPROCESSING
        print '\npostprocessing'
        matrices = {}
        for pp in pb.postprocess:
            if pp['kind'] in ['GaNi', 'gani']:
                order_name = ''
                Nname = ''
                A = mat.get_A_GaNi(pb.solve['N'], primaldual)
            elif pp['kind'] in ['Ga', 'ga']:
                Nbarpp = 2*pb.solve['N'] - 1
                if pp['order'] is None:
                    Nname = ''
                    order_name = ''
                    A = mat.get_A_Ga(Nbar=Nbarpp, order=pp['order'],
                                     primaldual=primaldual)
                else:
                    order_name = '_o' + str(pp['order'])
                    Nname = '_n%d' % np.mean(pp['M'])
                    A = mat.get_A_Ga(Nbar=Nbarpp, order=pp['order'],
                                     M=pp['M'], primaldual=primaldual)
            else:
                ValueError()

            name = 'AH_%s%s%s_%s' % (pp['kind'], order_name, Nname, primaldual)
            print 'calculate: ' + name

            AH = assembly_matrix(A, solutions)

            if primaldual is 'primal':
                matrices[name] = AH
            else:
                matrices[name] = np.linalg.inv(AH)

        pb.output.update({'sol_' + primaldual: solutions,
                          'res_' + primaldual: results,
                          'mat_' + primaldual: matrices})


def assembly_matrix(Afun, solutions):
    dim = len(solutions)
    if not np.allclose(Afun.N, solutions[0].N):
        Nbar = Afun.N
        for ii in np.arange(dim):
            solutions[ii] = solutions[ii].resize(Nbar)

    AH = np.zeros([dim, dim])
    for ii in np.arange(dim):
        for jj in np.arange(dim):
            AH[ii, jj] = Afun(solutions[ii])*solutions[jj]
    return AH


def add_macro2minimizer(X, E):
    if np.allclose(X.mean(), E):
        return X
    elif np.allclose(X.mean(), np.zeros_like(E)):
        return X + VecTri(name='EN', macroval=E, N=X.N)
    else:
        raise ValueError()

if __name__ == '__main__':
    execfile('../main_test.py')
