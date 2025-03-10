"""Cluster functions."""

__all__: list[str] = []

from functools import partial

import jax
from plum import convert, dispatch

import coordinax as cx
import quaxed.numpy as jnp
import unxt as u

import galax.coordinates as gc
import galax.potential as gp
import galax.typing as gt
from .api import L1L2LagrangePoints
from .radius import tidal_radius_king1962


@dispatch
@partial(jax.jit)
def lagrange_points(
    potential: gp.AbstractPotential,
    x: gt.LengthSz3 | cx.vecs.AbstractPos3D,
    v: gt.SpeedSz3 | cx.vecs.AbstractVel3D,
    /,
    *,
    mass: gt.MassSz0,
    t: gt.TimeSz0,
) -> L1L2LagrangePoints:
    """Compute the lagrange points of a cluster in a host potential.

    Parameters
    ----------
    potential : `galax.potential.AbstractPotential`
        The gravitational potential of the host.
    x: Quantity[float, (3,), "length"]
        Cartesian 3D position ($x$, $y$, $z$)
    v: Quantity[float, (3,), "speed"]
        Cartesian 3D velocity ($v_x$, $v_y$, $v_z$)
    mass: Quantity[float, (), "mass"]
        Cluster mass.
    t: Quantity[float, (), "time"]
        Time.

    Examples
    --------
    >>> import unxt as u
    >>> import galax.potential as gp
    >>> from galax.dynamics.cluster import lagrange_points

    >>> pot = gp.MilkyWayPotential()
    >>> x = u.Quantity([8.0, 0.0, 0.0], "kpc")
    >>> v = u.Quantity([0.0, 220.0, 0.0], "km/s")
    >>> mass = u.Quantity(1e4, "Msun")
    >>> t = u.Quantity(0.0, "Gyr")

    >>> lpts = lagrange_points(pot, x, v, mass=mass, t=t)
    >>> lpts.l1
    Quantity['length'](Array([7.97070926, 0. , 0. ], dtype=float64), unit='kpc')
    >>> lpts.l2
    Quantity['length'](Array([8.02929074, 0. , 0. ], dtype=float64), unit='kpc')

    This also works with `coordinax` vectors:

    >>> import coordinax as cx
    >>> lpts2 = lagrange_points(
    ...     pot, cx.CartesianPos3D.from_(x), cx.CartesianVel3D.from_(v), mass=mass, t=t
    ... )
    >>> lpts2.l1
    Quantity['length'](Array([7.97070926, 0. , 0. ], dtype=float64), unit='kpc')
    >>> lpts2.l2
    Quantity['length'](Array([8.02929074, 0. , 0. ], dtype=float64), unit='kpc')

    """
    x = convert(x, u.Quantity)
    v = convert(v, u.Quantity)
    r_t = tidal_radius_king1962(potential, x, v, mass=mass, t=t)
    r_hat = cx.vecs.normalize_vector(x)
    l1 = x - r_hat * r_t  # close
    l2 = x + r_hat * r_t  # far
    return L1L2LagrangePoints(l1=l1, l2=l2)


@dispatch
def lagrange_points(
    pot: gp.AbstractPotential,
    space: cx.Space,
    /,
    *,
    mass: gt.MassSz0,
    t: gt.TimeSz0,
) -> L1L2LagrangePoints:
    """Compute the lagrange points of a cluster in a host potential.

    Examples
    --------
    >>> import unxt as u
    >>> import galax.potential as gp
    >>> from galax.dynamics.cluster import lagrange_points

    >>> pot = gp.MilkyWayPotential()
    >>> x = cx.CartesianPos3D.from_(u.Quantity([8.0, 0.0, 0.0], "kpc"))
    >>> v = cx.CartesianVel3D.from_(u.Quantity([0.0, 220.0, 0.0], "km/s"))
    >>> mass = u.Quantity(1e4, "Msun")
    >>> t = u.Quantity(0.0, "Gyr")

    This also works with a `coordinax.Space` object:

    >>> import coordinax as cx
    >>> space = cx.Space(length=x, speed=v)
    >>> lpts = lagrange_points(pot, space, mass=mass, t=t)
    >>> lpts.l1
    Quantity['length'](Array([7.97070926, 0. , 0. ], dtype=float64), unit='kpc')
    >>> lpts.l2
    Quantity['length'](Array([8.02929074, 0. , 0. ], dtype=float64), unit='kpc')

    """
    return lagrange_points(pot, space["length"], space["speed"], mass=mass, t=t)


@dispatch
def lagrange_points(
    pot: gp.AbstractPotential,
    coord: cx.frames.AbstractCoordinate,
    /,
    *,
    mass: gt.MassSz0,
    t: gt.TimeSz0,
) -> L1L2LagrangePoints:
    """Compute the lagrange points of a cluster in a host potential.

    Examples
    --------
    >>> import unxt as u
    >>> import galax.potential as gp
    >>> from galax.dynamics.cluster import lagrange_points

    >>> pot = gp.MilkyWayPotential()
    >>> x = cx.CartesianPos3D.from_(u.Quantity([8.0, 0.0, 0.0], "kpc"))
    >>> v = cx.CartesianVel3D.from_(u.Quantity([0.0, 220.0, 0.0], "km/s"))
    >>> mass = u.Quantity(1e4, "Msun")
    >>> t = u.Quantity(0.0, "Gyr")

    This also works with a `coordinax.Coordinate` object:

    >>> import coordinax as cx
    >>> space = cx.Coordinate(cx.Space(length=x, speed=v), frame=cx.frames.ICRS())
    >>> lpts = lagrange_points(pot, space, mass=mass, t=t)
    >>> lpts.l1
    Quantity['length'](Array([7.97070926, 0. , 0. ], dtype=float64), unit='kpc')
    >>> lpts.l2
    Quantity['length'](Array([8.02929074, 0. , 0. ], dtype=float64), unit='kpc')

    """
    return lagrange_points(pot, coord.data, mass=mass, t=t)


@dispatch
def lagrange_points(
    pot: gp.AbstractPotential,
    w: gc.AbstractPhaseSpaceCoordinate,
    /,
    *,
    mass: gt.MassSz0,
) -> L1L2LagrangePoints:
    """Compute the lagrange points of a cluster in a host potential.

    Examples
    --------
    >>> import unxt as u
    >>> import galax.potential as gp
    >>> from galax.dynamics.cluster import lagrange_points

    >>> pot = gp.MilkyWayPotential()
    >>> x = cx.CartesianPos3D.from_(u.Quantity([8.0, 0.0, 0.0], "kpc"))
    >>> v = cx.CartesianVel3D.from_(u.Quantity([0.0, 220.0, 0.0], "km/s"))
    >>> mass = u.Quantity(1e4, "Msun")
    >>> t = u.Quantity(0.0, "Gyr")

    This also works with a `galax.coordinates.PhaseSpaceCoordinate` object:

    >>> import galax.coordinates as gc
    >>> w = gc.PhaseSpaceCoordinate(q=x, p=v, t=t)
    >>> lpts = lagrange_points(pot, w, mass=mass)
    >>> lpts.l1
    Quantity['length'](Array([7.97070926, 0. , 0. ], dtype=float64), unit='kpc')
    >>> lpts.l2
    Quantity['length'](Array([8.02929074, 0. , 0. ], dtype=float64), unit='kpc')

    """
    return lagrange_points(pot, w.q, w.p, mass=mass, t=w.t.squeeze())


@dispatch
def lagrange_points(
    pot: gp.AbstractPotential,
    w: gc.PhaseSpacePosition,
    /,
    *,
    mass: gt.MassSz0,
    time: gt.TimeSz0,
) -> L1L2LagrangePoints:
    """Compute the lagrange points of a cluster in a host potential.

    Examples
    --------
    >>> import unxt as u
    >>> import galax.potential as gp
    >>> from galax.dynamics.cluster import lagrange_points

    >>> pot = gp.MilkyWayPotential()
    >>> x = cx.CartesianPos3D.from_(u.Quantity([8.0, 0.0, 0.0], "kpc"))
    >>> v = cx.CartesianVel3D.from_(u.Quantity([0.0, 220.0, 0.0], "km/s"))
    >>> mass = u.Quantity(1e4, "Msun")
    >>> t = u.Quantity(0.0, "Gyr")

    This also works with a `galax.coordinates.PhaseSpacePosition` object:

    >>> import galax.coordinates as gc
    >>> w = gc.PhaseSpacePosition(q=x, p=v)
    >>> lpts = lagrange_points(pot, w, mass=mass, time=t)
    >>> lpts.l1
    Quantity['length'](Array([7.97070926, 0. , 0. ], dtype=float64), unit='kpc')
    >>> lpts.l2
    Quantity['length'](Array([8.02929074, 0. , 0. ], dtype=float64), unit='kpc')

    """
    return lagrange_points(pot, w.q, w.p, mass=mass, t=time)


@dispatch
@partial(jax.jit)
def relaxation_time(
    Mc: u.AbstractQuantity,
    r_hm: u.AbstractQuantity,
    m_avg: u.AbstractQuantity,
    /,
    *,
    G: u.AbstractQuantity,
) -> u.AbstractQuantity:
    """Compute the cluster's relaxation time.

    Baumgardt 1998 Equation 1.

    """
    N = Mc / m_avg
    return 0.138 * jnp.sqrt(Mc * r_hm**3 / G / m_avg**2) / jnp.log(0.4 * N)
