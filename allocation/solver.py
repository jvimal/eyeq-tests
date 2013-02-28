from cvxpy import *
import random
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import multiprocessing
import time
import argparse

"""
A simple solver for the simplest non-trivial instance of the
performance isolation problem.  Four flows, two tenants, two machines,
etc.

TODO: generalise this using matrices by reading from the topology
file.  This is just to visualise the trajectories in 3D.
"""

parser = argparse.ArgumentParser()
parser.add_argument('--precision',
                    default=5,
                    type=int)

parser.add_argument('--num-trajectories', '-n',
                    default=100,
                    type=int)

parser.add_argument('--out', '-o',
                    default="test.pdf")

args = parser.parse_args()

PRECISION = 5
FMT = '%%.%df' % PRECISION

def U(xs):
    """This approximates the max-min utility function."""
    ret = 0
    for x in xs:
        ret += log(x)
    return ret

def config(p):
    return
    p.options['maxiters'] = 200
    p.options['feastol'] = 1e-7
    p.options['reltol'] = 1e-7

def tenant(Cs):
    """
    The tenant optimisation problem.  Returns a vector of allocations
    to flows.
    """
    xs = [variable() for i in xrange(4)]
    constraints = []
    def _(blah):
        constraints.append(blah)
    for x in xs:
        _(geq(x, 0))
    _(leq(xs[0] + xs[1], Cs[0]))
    _(leq(xs[0], Cs[3]))
    _(leq(xs[1], Cs[4]))
    _(leq(xs[2], Cs[1]))
    _(leq(xs[3], Cs[2]))
    _(leq(xs[2] + xs[3], Cs[5]))

    p = program(maximize(U(xs)), constraints)
    config(p)
    #p.show()
    p.solve(quiet=True)

    return [x.value for x in xs]

def provider(Xs, eps=0.1):
    """Provider solves another optimisation problem."""
    ys = [variable() for i in xrange(6)]
    constraints = []
    def _(blah):
        constraints.append(blah)
    for y in ys:
        _(geq(y, 0))
    _(leq(ys[0] + ys[1] + ys[2], 1))
    _(leq(ys[3] + ys[4] + ys[5], 1))
    _(leq(ys[0], Xs[0] + Xs[1] + eps))
    _(leq(ys[1], Xs[2] + eps))
    _(leq(ys[2], Xs[3] + eps))
    _(leq(ys[3], Xs[0] + eps))
    _(leq(ys[4], Xs[1] + eps))
    _(leq(ys[5], Xs[2] + Xs[3] + eps))

    p = program(maximize(U(ys)), constraints)
    config(p)
    #p.show()
    p.solve(quiet=True)

    return [y.value for y in ys]

def random_provider():
    def rand():
        r = 0.0
        while r == 0.0:
            r = random.random()
        return r

    x0 = rand()
    x1 = rand()
    y0 = rand()
    y1 = rand()

    return [x0, x1, 1-x0-x1, y0, y1, 1-y0-y1]

def __(arr):
    return [FMT % f for f in arr]

def iterates(iter_num=0, verbose=False):
    P = random_provider()
    prev = __(P)
    curr = None
    seen = []
    if verbose:
        print "starting with", prev
    T = tenant(P)
    iter = 200
    eps = 0.01
    while iter:
        iter -= 1
        P = provider(T, eps)
        T = tenant(P)
        curr = __(T)
        if verbose:
            print curr,sum(T)
        if curr == prev:
            if verbose:
                print 'fixed point', curr
            break
        elif curr in seen:
            L = seen.index(curr)
            L = len(seen) - L
            if verbose:
                print 'limit cycle of length', L
            break
        else:
            prev = curr
            seen.append(curr)
    print 'finished %d' % iter_num, curr
    return map(lambda lst: map(float, lst), seen)

def distance(a, b):
    return sum([abs(ai - bi) for (ai, bi) in zip(a, b)])

def pick_solution(sol):
    sols = [ [1.0/6, 1.0/6, 1.0/3, 1.0/3],
             [1.0/3, 1.0/3, 1.0/6, 1.0/6],
             [1.0/4, 1.0/4, 1.0/4, 1.0/4] ]
    dist = 100
    closest = None
    for i, s in enumerate(sols):
        d = distance(s, sol)
        if d < dist:
            dist = d
            closest = s
    return closest

def plot_trajectories(num_samples):
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    p = multiprocessing.Pool(4)
    iters = p.map(iterates, range(num_samples))
    soln = []
    for iter in iters:
        # Take only the first 3 coords
        xs = map(lambda e: e[0], iter)
        ys = map(lambda e: e[1], iter)
        zs = map(lambda e: e[2], iter)
        sol = iter[-1]

        ax.plot(xs, ys, zs)
        ax.plot([sol[0]],
                [sol[1]],
                [sol[2]], marker='o', color='grey', markersize=7, alpha=0.2)
        soln.append(sol)

        chosen = pick_solution(sol)
        ax.plot([chosen[0]],
                [chosen[1]],
                [chosen[2]],
                marker='s', color='blue', markersize=8, alpha=0.2)

    for sol in soln:
        print sol

    if args.out:
        plt.savefig(args.out)
        ax.set_xlim((0.10, 0.4))
        ax.set_ylim((0.10, 0.4))
        ax.set_zlim((0.10, 0.4))
        fname = args.out.split('.')[0]
        plt.savefig(fname + "-zoom.pdf")
    plt.show()

start = time.time()
plot_trajectories(args.num_trajectories)
end = time.time()
print 'Took %.2f seconds' % (end - start)
