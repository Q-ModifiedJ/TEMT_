import math
import numpy as np

hartmann3_alpha = [1.0, 1.2, 3.0, 3.2]
hartmann3_A = [[3.0, 10, 30],
               [0.1, 10, 30],
               [3.0, 10, 30],
               [0.1, 10, 35]]
hartmann3_P = [[0.3689, 0.1170, 0.2673],
               [0.4699, 0.4387, 0.7470],
               [0.1091, 0.8732, 0.5547],
               [0.0381, 0.5743, 0.8828]]
hartmann3_best_x = [0.114614, 0.555649, 0.852547]

hartmann3_best = -3.903864585120031411269484676


def hartmann3(x):
    global hartmann3_alpha, hartmann3_A, hartmann3_P
    if len(x) != 3:
        return 0

    res = 0
    for i in range(4):
        tmp = 0
        for j in range(3):
            tmp += - hartmann3_A[i][j] * ((x[j] - hartmann3_P[i][j]) ** 2)
        res += - (hartmann3_alpha[i]) * math.exp(tmp)
    return res


def hartmann3_w_AGN(x, sigma):
    res = hartmann3(x)
    res += float(np.random.normal(0, sigma, 1))
    return res

# hartmann3_best = hartmann3(hartmann3_best_x)
