"""
Compact NSGA-II (Deb et al., 2002) with constrained domination, SBX crossover and polynomial
mutation, written in NumPy (pymoo is not available in the build environment; the algorithm and
operators follow pymoo's defaults: SBX eta 15, p_c 0.9; PM eta 20, p_m 1/n_var).
"""
import numpy as np


def fast_nondominated_sort(F, CV):
    """Constrained domination: feasible beats infeasible; lower CV wins among infeasible."""
    n = len(F)
    feas = CV == 0
    le = np.all(F[:, None, :] <= F[None, :, :], axis=2)
    lt = np.any(F[:, None, :] < F[None, :, :], axis=2)
    D = le & lt & feas[:, None] & feas[None, :]                  # both feasible: Pareto
    D |= feas[:, None] & ~feas[None, :]                           # feasible beats infeasible
    D |= (~feas[:, None]) & (~feas[None, :]) & (CV[:, None] < CV[None, :])
    S = [np.nonzero(D[p])[0].tolist() for p in range(n)]
    cnt = D.sum(axis=0)
    fronts = [np.nonzero(cnt == 0)[0].tolist()]
    i = 0
    while fronts[i]:
        nxt = []
        for p in fronts[i]:
            for q in S[p]:
                cnt[q] -= 1
                if cnt[q] == 0:
                    nxt.append(q)
        i += 1
        fronts.append(nxt)
    return fronts[:-1]


def dominates(fa, ca, fb, cb):
    if ca == 0 and cb > 0:
        return True
    if ca > 0 and cb == 0:
        return False
    if ca > 0 and cb > 0:
        return ca < cb
    return np.all(fa <= fb) and np.any(fa < fb)


def crowding(F):
    n, m = F.shape
    d = np.zeros(n)
    if n <= 2:
        return np.full(n, np.inf)
    for j in range(m):
        idx = np.argsort(F[:, j])
        d[idx[0]] = d[idx[-1]] = np.inf
        span = F[idx[-1], j] - F[idx[0], j]
        if span <= 0:
            continue
        d[idx[1:-1]] += (F[idx[2:], j] - F[idx[:-2], j]) / span
    return d


def sbx(p1, p2, lo, hi, rng, eta=15.0, pc=0.9):
    c1, c2 = p1.copy(), p2.copy()
    if rng.random() > pc:
        return c1, c2
    for i in range(len(p1)):
        if rng.random() > 0.5 or abs(p1[i] - p2[i]) < 1e-12:
            continue
        u = rng.random()
        beta = (2 * u) ** (1 / (eta + 1)) if u <= 0.5 else (1 / (2 * (1 - u))) ** (1 / (eta + 1))
        c1[i] = 0.5 * ((1 + beta) * p1[i] + (1 - beta) * p2[i])
        c2[i] = 0.5 * ((1 - beta) * p1[i] + (1 + beta) * p2[i])
    return np.clip(c1, lo, hi), np.clip(c2, lo, hi)


def pmut(x, lo, hi, rng, eta=20.0):
    y = x.copy()
    pm = 1.0 / len(x)
    for i in range(len(x)):
        if rng.random() < pm:
            u = rng.random()
            d = (2 * u) ** (1 / (eta + 1)) - 1 if u < 0.5 else 1 - (2 * (1 - u)) ** (1 / (eta + 1))
            y[i] += d * (hi[i] - lo[i])
    return np.clip(y, lo, hi)


def nsga2(func, lo, hi, pop=80, gens=120, seed=1):
    """func(x) -> (F (n_obj,), CV scalar >= 0, payload). Returns final population + archive."""
    rng = np.random.default_rng(seed)
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    X = lo + rng.random((pop, len(lo))) * (hi - lo)
    evals = [func(x) for x in X]
    archive = list(evals)
    F = np.array([e[0] for e in evals]); CV = np.array([e[1] for e in evals])
    for _ in range(gens):
        # rank + crowding for tournament
        fronts = fast_nondominated_sort(F, CV)
        rank = np.empty(pop, int)
        cd = np.empty(pop)
        for k, fr in enumerate(fronts):
            rank[fr] = k
            cd[fr] = crowding(F[fr])
        kids = []
        while len(kids) < pop:
            a, b = rng.integers(pop, size=2), rng.integers(pop, size=2)
            pick = lambda t: t[0] if (rank[t[0]] < rank[t[1]] or (rank[t[0]] == rank[t[1]] and cd[t[0]] > cd[t[1]])) else t[1]
            c1, c2 = sbx(X[pick(a)], X[pick(b)], lo, hi, rng)
            kids += [pmut(c1, lo, hi, rng), pmut(c2, lo, hi, rng)]
        Xk = np.array(kids[:pop])
        ek = [func(x) for x in Xk]
        archive += ek
        Xa = np.vstack([X, Xk]); ea = evals + ek
        Fa = np.array([e[0] for e in ea]); CVa = np.array([e[1] for e in ea])
        fronts = fast_nondominated_sort(Fa, CVa)
        keep = []
        for fr in fronts:
            if len(keep) + len(fr) <= pop:
                keep += fr
            else:
                d = crowding(Fa[fr])
                keep += [fr[i] for i in np.argsort(-d)[:pop - len(keep)]]
                break
        X, evals = Xa[keep], [ea[i] for i in keep]
        F, CV = Fa[keep], CVa[keep]
    return evals, archive
