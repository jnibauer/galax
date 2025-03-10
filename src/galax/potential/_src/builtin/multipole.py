"""Multipole potential."""

__all__ = [
    "AbstractMultipolePotential",
    "MultipoleInnerPotential",
    "MultipoleOuterPotential",
    "MultipolePotential",
]

from dataclasses import KW_ONLY
from functools import partial
from typing import final

import jax
from equinox import field
from jax.scipy.special import sph_harm
from jaxtyping import Array, Float

import quaxed.numpy as jnp
import unxt as u

import galax.typing as gt
from galax.potential._src.base_single import AbstractSinglePotential
from galax.potential._src.params.core import AbstractParameter
from galax.potential._src.params.field import ParameterField
from galax.utils._unxt import AllowValue


class AbstractMultipolePotential(AbstractSinglePotential):
    """Abstract Multipole Potential."""

    m_tot: AbstractParameter = ParameterField(dimensions="mass")  # type: ignore[assignment]
    """Total mass of the multipole potential."""

    r_s: AbstractParameter = ParameterField(dimensions="length")  # type: ignore[assignment]
    """Scale radius."""

    _: KW_ONLY
    l_max: int = field(static=True)


@final
class MultipoleInnerPotential(AbstractMultipolePotential):
    r"""Multipole inner expansion potential.

    .. math::

        \Phi^l_\mathrm{max}(r,\theta,\phi) =
            \sum_{l=0}^{l=l_\mathrm{max}}\sum_{m=0}^{m=l}
            r^l \, (S_{lm} \, \cos{m\,\phi} + T_{lm} \, \sin{m\,\phi})
            \, P_l^m(\cos\theta)

    """

    Slm: AbstractParameter = ParameterField(dimensions="dimensionless")  # type: ignore[assignment]
    r"""Spherical harmonic coefficients for the $\cos(m \phi)$ terms."""

    Tlm: AbstractParameter = ParameterField(dimensions="dimensionless")  # type: ignore[assignment]
    r"""Spherical harmonic coefficients for the $\sin(m \phi)$ terms."""

    def __check_init__(self) -> None:
        shape = (self.l_max + 1, self.l_max + 1)
        t = u.Quantity(0.0, "Gyr")
        s_shape, t_shape = self.Slm(t).shape, self.Tlm(t).shape
        # TODO: check shape across time.
        if s_shape != shape or t_shape != shape:
            msg = (
                "Slm and Tlm must have the shape (l_max + 1, l_max + 1)."
                f"Slm shape: {s_shape}, Tlm shape: {t_shape}"
            )
            raise ValueError(msg)

    @partial(jax.jit)
    def _potential(
        self, xyz: gt.BtQuSz3 | gt.BtSz3, t: gt.BBtRealQuSz0 | gt.BBtRealSz0, /
    ) -> gt.BtFloatSz0:
        # Compute the params
        m_tot = self.m_tot(t, ustrip=self.units["mass"])
        r_s = self.r_s(t, ustrip=self.units["length"])
        Slm = self.Slm(t, ustrip=self.units["dimensionless"])
        Tlm = self.Tlm(t, ustrip=self.units["dimensionless"])
        xyz = u.ustrip(AllowValue, self.units["length"], xyz)

        # spherical coordinates
        is_scalar = xyz.ndim == 1
        s, theta, phi = cartesian_to_normalized_spherical(jnp.atleast_2d(xyz), r_s)

        # Compute the summation over l and m
        l_max = self.l_max
        ls, ms = jnp.tril_indices(l_max + 1)

        # TODO: vectorize compute_Ylm over l, m, then don't need a vmap?
        def summand(l: int, m: int) -> Float[Array, "*batch"]:
            cPlm, sPlm = compute_Ylm(l, m, theta, phi, l_max=l_max)
            return jnp.pow(s, l) * (Slm[l, m] * cPlm + Tlm[l, m] * sPlm)

        summation = jnp.sum(jax.vmap(summand, in_axes=(0, 0))(ls, ms), axis=0)
        if is_scalar:
            summation = summation[0]

        return self.constants["G"].value * m_tot / r_s * summation


@final
class MultipoleOuterPotential(AbstractMultipolePotential):
    r"""Multipole outer expansion potential.

    .. math::

        \Phi^l_\mathrm{max}(r,\theta,\phi) =
            \sum_{l=0}^{l=l_\mathrm{max}}\sum_{m=0}^{m=l}
            r^{-(l+1)} \, (S_{lm} \, \cos{m\,\phi} + T_{lm} \, \sin{m\,\phi})
            \, P_l^m(\cos\theta)

    """

    Slm: AbstractParameter = ParameterField(dimensions="dimensionless")  # type: ignore[assignment]
    r"""Spherical harmonic coefficients for the $\cos(m \phi)$ terms."""

    Tlm: AbstractParameter = ParameterField(dimensions="dimensionless")  # type: ignore[assignment]
    r"""Spherical harmonic coefficients for the $\sin(m \phi)$ terms."""

    def __check_init__(self) -> None:
        shape = (self.l_max + 1, self.l_max + 1)
        t = u.Quantity(0.0, "Gyr")
        s_shape, t_shape = self.Slm(t).shape, self.Tlm(t).shape
        # TODO: check shape across time.
        if s_shape != shape or t_shape != shape:
            msg = (
                "Slm and Tlm must have the shape (l_max + 1, l_max + 1)."
                f"Slm shape: {s_shape}, Tlm shape: {t_shape}"
            )
            raise ValueError(msg)

    @partial(jax.jit)
    def _potential(
        self, xyz: gt.BtQuSz3 | gt.BtSz3, t: gt.BBtRealQuSz0 | gt.BBtRealSz0, /
    ) -> gt.BtFloatSz0:
        # Compute the parameters
        m_tot = self.m_tot(t, ustrip=self.units["mass"])
        r_s = self.r_s(t, ustrip=self.units["length"])
        Slm = self.Slm(t, ustrip=self.units["dimensionless"])
        Tlm = self.Tlm(t, ustrip=self.units["dimensionless"])
        xyz = u.ustrip(AllowValue, self.units["length"], xyz)

        # spherical coordinates
        is_scalar = xyz.ndim == 1
        s, theta, phi = cartesian_to_normalized_spherical(jnp.atleast_2d(xyz), r_s)

        # Compute the summation over l and m
        l_max = self.l_max
        ls, ms = jnp.tril_indices(l_max + 1)

        # TODO: vectorize compute_Ylm over l, m, then don't need a vmap?
        def summand(l: int, m: int) -> Float[Array, "*batch"]:
            cPlm, sPlm = compute_Ylm(l, m, theta, phi, l_max=l_max)
            return jnp.pow(s, -(l + 1)) * (Slm[l, m] * cPlm + Tlm[l, m] * sPlm)

        summation = jnp.sum(jax.vmap(summand, in_axes=(0, 0))(ls, ms), axis=0)
        if is_scalar:
            summation = summation[0]

        return self.constants["G"].value * m_tot / r_s * summation


@final
class MultipolePotential(AbstractMultipolePotential):
    r"""Multipole inner and outer expansion potential.

    .. math::

        \Phi^l_\mathrm{max}(r,\theta,\phi) =
            \sum_{l=0}^{l=l_\mathrm{max}}\sum_{m=0}^{m=l}
            [  (r^l IS_{lm} + r^{-(l+1)} OS_{lm}) \, \cos{m\,\phi}
             + (r^l IT_{lm} + r^{-(l+1)} OT_{lm}) \, \sin{m\,\phi}]
            \, P_l^m(\cos\theta)

    """

    ISlm: AbstractParameter = ParameterField(dimensions="dimensionless")  # type: ignore[assignment]
    r"""Inner spherical harmonic coefficients for the $\cos(m \phi)$ terms."""

    ITlm: AbstractParameter = ParameterField(dimensions="dimensionless")  # type: ignore[assignment]
    r"""Inner Spherical harmonic coefficients for the $\sin(m \phi)$ terms."""

    OSlm: AbstractParameter = ParameterField(dimensions="dimensionless")  # type: ignore[assignment]
    r"""Outer spherical harmonic coefficients for the $\cos(m \phi)$ terms."""

    OTlm: AbstractParameter = ParameterField(dimensions="dimensionless")  # type: ignore[assignment]
    r"""Outer Spherical harmonic coefficients for the $\sin(m \phi)$ terms."""

    def __check_init__(self) -> None:
        shape = (self.l_max + 1, self.l_max + 1)
        t = u.Quantity(0.0, "Gyr")
        is_shape, it_shape = self.ISlm(t).shape, self.ITlm(t).shape
        os_shape, ot_shape = self.OSlm(t).shape, self.OTlm(t).shape
        # TODO: check shape across time.
        if (
            is_shape != shape
            or it_shape != shape
            or os_shape != shape
            or ot_shape != shape
        ):
            msg = "I/OSlm and I/OTlm must have the shape (l_max + 1, l_max + 1)."
            raise ValueError(msg)

    @partial(jax.jit)
    def _potential(
        self, xyz: gt.BtQuSz3 | gt.BtSz3, t: gt.BBtRealQuSz0 | gt.BBtRealSz0, /
    ) -> gt.BtFloatSz0:
        # Compute the parameters
        u1 = self.units["dimensionless"]
        m_tot = self.m_tot(t, ustrip=self.units["mass"])
        r_s = self.r_s(t, ustrip=self.units["length"])
        ISlm, ITlm = self.ISlm(t, ustrip=u1), self.ITlm(t, ustrip=u1)
        OSlm, OTlm = self.OSlm(t, ustrip=u1), self.OTlm(t, ustrip=u1)

        xyz = u.ustrip(AllowValue, self.units["length"], xyz)

        # spherical coordinates
        is_scalar = xyz.ndim == 1
        s, theta, phi = cartesian_to_normalized_spherical(jnp.atleast_2d(xyz), r_s)

        # Compute the summation over l and m
        l_max = self.l_max
        ls, ms = jnp.tril_indices(l_max + 1)

        # TODO: vectorize compute_Ylm over l, m, then don't need a vmap?
        def summand(l: int, m: int) -> Float[Array, "*batch"]:
            cPlm, sPlm = compute_Ylm(l, m, theta, phi, l_max=l_max)
            inner = jnp.pow(s, l) * (ISlm[l, m] * cPlm + ITlm[l, m] * sPlm)
            outer = jnp.pow(s, -l - 1) * (OSlm[l, m] * cPlm + OTlm[l, m] * sPlm)
            return inner + outer

        summation = jnp.sum(jax.vmap(summand, in_axes=(0, 0))(ls, ms), axis=0)
        if is_scalar:
            summation = summation[0]

        return self.constants["G"].value * m_tot / r_s * summation


# ===== Helper functions =====


def cartesian_to_normalized_spherical(
    q: gt.BtSz3, r_s: gt.Sz0, /
) -> tuple[gt.BtFloatSz0, gt.BtFloatSz0, gt.BtFloatSz0]:
    r"""Convert Cartesian coordinates to normalized spherical coordinates.

    .. math::

        r = \sqrt{x^2 + y^2 + z^2}
        X = \cos(\theta) = z / r
        \phi = \tan^{-1}\left(\frac{y}{x}\right)

    """
    r = jnp.linalg.vector_norm(q, axis=-1)
    s = r / r_s
    theta = jnp.acos(q[..., 2] / r)  # theta
    phi = jnp.atan2(q[..., 1], q[..., 0])  # atan(y/x)
    return s, theta, phi


# TODO: vectorize such that it's signature="(l),(l),(N),(N)->(l, N)":
def compute_Ylm(
    l: int,
    m: int,
    theta: Float[Array, "*batch"],
    phi: Float[Array, "*batch"],
    *,
    l_max: int,
) -> tuple[Float[Array, "*batch"], Float[Array, "*batch"]]:
    Ylm = sph_harm(jnp.atleast_1d(m), jnp.atleast_1d(l), phi, theta, n_max=l_max)
    return Ylm.real, Ylm.imag
