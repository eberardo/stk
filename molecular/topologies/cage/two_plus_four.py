"""
Defines cage topologies from di and 4 functionalised building blocks.

"""


import numpy as np

from .base import _CageTopology,  Vertex, Edge


class TwoPlusFour(_CageTopology):
    """
    Sandwich cage topology from 2 and 4 functionalized building blocks.

    """

    positions_A = [Vertex(0, 0, -1), Vertex(0, 0, 1)]
    alpha, beta = positions_A
    beta.edge_plane_normal = lambda scale, alpha=alpha: np.multiply(
                                        alpha.edge_plane_normal(scale), -1)

    positions_B = [Edge(alpha, beta),
                   Edge(alpha, beta),
                   Edge(alpha, beta),
                   Edge(alpha, beta)]

    a, b, c, d = positions_B

    a.coord = np.array([2, 0, 0])
    b.coord = np.array([-2, 0, 0])
    c.coord = np.array([0, 2, 0])
    d.coord = np.array([0, -2, 0])

    n_windows = 4
    n_window_types = 1


class ThreePlusSix(_CageTopology):
    """
    A cage topology from 2 and 4 functionalized building blocks.

    """
    x = 1
    positions_A = [Vertex(-2*x, -x*np.sqrt(3), 0),
                   Vertex(2*x, -x*np.sqrt(3), 0),
                   Vertex(0, x*np.sqrt(3), 0)]

    a, b, c = positions_A

    positions_B = [Edge(a, b, custom_position=True),
                   Edge(a, b, custom_position=True),
                   Edge(b, c, custom_position=True),
                   Edge(b, c, custom_position=True),
                   Edge(a, c, custom_position=True),
                   Edge(a, c, custom_position=True)]

    e1, e2, e3, e4, e5, e6 = positions_B
    for e in [e1, e3, e5]:
        e.coord = np.add(e.coord, [0, 0, x])

    for e in [e2, e4, e6]:
        e.coord = np.add(e.coord, [0, 0, -x])

    n_windows = 5
    n_window_types = 2


class FourPlusEight(_CageTopology):
    """
    A cage topology from 2 and 4 functionalized building blocks.

    """

    positions_A = [Vertex(-1, -1, 0),
                   Vertex(-1, 1, 0),
                   Vertex(1, -1, 0),
                   Vertex(1, 1, 0)]

    a, b, c, d = positions_A

    positions_B = [Edge(a, b, custom_position=True),
                   Edge(a, b, custom_position=True),
                   Edge(b, d, custom_position=True),
                   Edge(b, d, custom_position=True),
                   Edge(a, c, custom_position=True),
                   Edge(a, c, custom_position=True),
                   Edge(c, d, custom_position=True),
                   Edge(c, d, custom_position=True)]

    e1, e2, e3, e4, e5, e6, e7, e8 = positions_B
    for e in [e1, e3, e5, e7]:
        e.coord = np.add(e.coord, [0, 0, 1])

    for e in [e2, e4, e6, e8]:
        e.coord = np.add(e.coord, [0, 0, -1])

    n_windows = 6
    n_window_types = 2


class SixPlusTwelve(_CageTopology):
    """
    A cage topology from 2 and 4 functionalized building blocks.

    """

    positions_A = [Vertex(-1, -1, 0),
                   Vertex(-1, 1, 0),
                   Vertex(1, -1, 0),
                   Vertex(1, 1, 0),
                   Vertex(0, 0, 1),
                   Vertex(0, 0, -1)]

    a, b, c, d, e, f = positions_A

    positions_B = [Edge(a, b),
                   Edge(b, d),
                   Edge(d, c),
                   Edge(a, c),
                   Edge(e, a),
                   Edge(e, b),
                   Edge(e, c),
                   Edge(e, d),
                   Edge(f, a),
                   Edge(f, b),
                   Edge(f, c),
                   Edge(f, d)]

    n_windows = 8
    n_window_types = 1


class TenPlusTwenty(_CageTopology):
    """
    A cage topology from 2 and 4 functionalized building blocks.

    """

    x = 2
    positions_A = [Vertex(-x, x, -x),
                   Vertex(-x, -x, -x),
                   Vertex(x, x, -x),
                   Vertex(x, -x, -x),

                   Vertex(-x, x, x),
                   Vertex(-x, -x, x),
                   Vertex(x, x, x),
                   Vertex(x, -x, x),

                   Vertex(0, 0, x*1.5),
                   Vertex(0, 0, -x*1.5)]

    a, b, c, d, e, f, g, h, i, j = positions_A

    positions_B = [Edge(a, c),
                   Edge(a, b),
                   Edge(b, d),
                   Edge(c, d),

                   Edge(e, g),
                   Edge(e, f),
                   Edge(f, h),
                   Edge(g, h),


                   Edge(a, e),
                   Edge(b, f),
                   Edge(c, g),
                   Edge(d, h),

                   Edge(i, e),
                   Edge(i, f),
                   Edge(i, g),
                   Edge(i, h),

                   Edge(j, a),
                   Edge(j, b),
                   Edge(j, c),
                   Edge(j, d)]

    n_windows = 12
    n_window_types = 2
