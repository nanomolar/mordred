from collections import namedtuple

import numpy as np
from six import string_types

from ._base import Descriptor

Eig = namedtuple("eigen", "val vec min max")

methods = []


def method(cls):
    methods.append(cls)
    cls.as_argument = cls.__name__
    return cls


class Common(Descriptor):
    __slots__ = "matrix", "explicit_hydrogens", "kekulize"
    require_connected = True

    def parameters(self):
        return self.matrix, self.explicit_hydrogens, self.kekulize

    def __init__(self, matrix, explicit_hydrogens, kekulize):
        self.matrix = matrix
        self.explicit_hydrogens = explicit_hydrogens
        self.kekulize = kekulize

    @property
    def _key_args(self):
        return (
            self.matrix,
            self.explicit_hydrogens,
            self.kekulize,
        )

    def dependencies(self):
        return {"eig": Eigen(*self._key_args)}

    @property
    def _eig(self):
        return Eigen(*self._key_args)

    @property
    def _SpMax(self):
        return SpMax(*self._key_args)

    @property
    def _SpMean(self):
        return SpMean(*self._key_args)

    @property
    def _SpAD(self):
        return SpAD(*self._key_args)

    @property
    def _VE1(self):
        return VE1(*self._key_args)

    @property
    def _VR1(self):
        return VR1(*self._key_args)

    def __str__(self):
        n = self.__class__.__name__

        if self.kekulize:
            n += "K"

        if self.explicit_hydrogens:
            n += "H"

        return n


class Eigen(Common):
    __slots__ = ()

    def dependencies(self):
        return {"matrix": self.matrix}

    def calculate(self, matrix):
        if matrix is None:
            raise ValueError("matrix is None")

        w, v = np.linalg.eig(matrix)

        if np.iscomplexobj(w):
            w = w.real

        if np.iscomplexobj(v):
            v = v.real

        i_min = np.argmin(w)
        i_max = np.argmax(w)

        return Eig(w, v, i_min, i_max)


@method
class SpAbs(Common):
    __slots__ = ()

    @classmethod
    def description(cls):
        return "graph energy"

    def calculate(self, eig):
        return np.abs(eig.val).sum()


@method
class SpMax(Common):
    __slots__ = ()

    @classmethod
    def description(cls):
        return "leading eigenvalue"

    def calculate(self, eig):
        return eig.val[eig.max]


@method
class SpDiam(Common):
    __slots__ = ()

    @classmethod
    def description(cls):
        return "spectral diamiter"

    def dependencies(self):
        return {
            "SpMax": self._SpMax,
            "eig": self._eig,
        }

    def calculate(self, SpMax, eig):
        return SpMax - eig.val[eig.min]


class SpMean(Common):
    __slots__ = ()

    @classmethod
    def description(cls):
        return "mean of eigenvalues"

    def calculate(self, eig):
        return np.mean(eig.val)


@method
class SpAD(Common):
    __slots__ = ()

    @classmethod
    def description(cls):
        return "spectral absolute diviation"

    def dependencies(self):
        return {
            "SpMean": self._SpMean,
            "eig": self._eig,
        }

    def calculate(self, eig, SpMean):
        return np.abs(eig.val - SpMean).sum()


@method
class SpMAD(Common):
    __slots__ = ()

    @classmethod
    def description(cls):
        return "spectral mean absolute diviation"

    def dependencies(self):
        return {"SpAD": self._SpAD}

    def calculate(self, SpAD):
        return SpAD / self.mol.GetNumAtoms()


@method
class LogEE(Common):
    __slots__ = ()

    @classmethod
    def description(cls):
        return "Estrada-like index"

    def calculate(self, eig):
        # log sum exp: https://hips.seas.harvard.edu/blog/2013/01/09/computing-log-sum-exp
        a = np.maximum(eig.val[eig.max], 0)
        sx = np.exp(eig.val - a).sum() + np.exp(-a)
        return a + np.log(sx)


@method
class SM1(Common):
    __slots__ = ()

    @classmethod
    def description(cls):
        return "spectral moment"

    def calculate(self, eig):
        return eig.val.sum()


@method
class VE1(Common):
    __slots__ = ()

    @classmethod
    def description(cls):
        return "coefficient sum of the last eigenvector"

    def calculate(self, eig):
        return np.abs(eig.vec[:, eig.max]).sum()


@method
class VE2(Common):
    __slots__ = ()

    @classmethod
    def description(cls):
        return "average coefficient of the last eigenvector"

    def dependencies(self):
        return {"VE1": self._VE1}

    def calculate(self, VE1):
        return VE1 / self.mol.GetNumAtoms()


@method
class VE3(Common):
    __slots__ = ()

    @classmethod
    def description(cls):
        return "logarithmic coefficient sum of the last eigenvector"

    def dependencies(self):
        return {"VE1": self._VE1}

    def calculate(self, VE1):
        with self.rethrow_zerodiv():
            return np.log(0.1 * self.mol.GetNumAtoms() * VE1)


@method
class VR1(Common):
    __slots__ = ()

    @classmethod
    def description(cls):
        return "Randic-like eigenvector-based index"

    def calculate(self, eig):
        s = 0.0

        for bond in self.mol.GetBonds():
            i = bond.GetBeginAtomIdx()
            j = bond.GetEndAtomIdx()

            s += (eig.vec[i, eig.max] * eig.vec[j, eig.max]) ** -0.5

        return s


@method
class VR2(Common):
    __slots__ = ()

    @classmethod
    def description(cls):
        return "normalized Randic-like eigenvector-based index"

    def dependencies(self):
        return {"VR1": self._VR1}

    def calculate(self, VR1):
        return VR1 / self.mol.GetNumAtoms()


@method
class VR3(Common):
    __slots__ = ()

    @classmethod
    def description(cls):
        return "logarithmic Randic-like eigenvector-based index"

    def dependencies(self):
        return {"VR1": self._VR1}

    def calculate(self, VR1):
        with self.rethrow_zerodiv():
            return np.log(0.1 * self.mol.GetNumAtoms() * VR1)


method_dict = {m.__name__: m for m in methods}


def get_method(n):
    if isinstance(n, string_types):
        return method_dict[n]

    return n
