import numpy as np

from . import _atomic_property
from ._base import Descriptor


class BCUTBase(Descriptor):
    explicit_hydrogens = False


class Burden(BCUTBase):
    def calculate(self, mol):
        N = mol.GetNumAtoms()

        mat = 0.001 * np.ones((N, N))

        for bond in mol.GetBonds():
            a = bond.GetBeginAtom()
            b = bond.GetEndAtom()
            i = a.GetIdx()
            j = b.GetIdx()

            try:
                w = bond.GetBondTypeAsDouble() / 10.0
            except RuntimeError:
                w = 1.0

            if a.GetDegree() == 1 or b.GetDegree() == 1:
                w += 0.01

            mat[i, j] = w
            mat[j, i] = w

        return mat


class BurdenEigenValues(BCUTBase):
    descriptor_keys = 'prop', 'gasteiger_charges'

    def __init__(self, prop, gasteiger_charges):
        self.prop = prop
        self.gasteiger_charges = gasteiger_charges

    def dependencies(self):
        return dict(burden=Burden())

    def calculate(self, mol, burden):
        bmat = burden.copy()
        ps = np.array([self.prop(a) for a in mol.GetAtoms()])
        if np.any(np.isnan(ps)):
            return np.array([np.nan])

        np.fill_diagonal(bmat, ps)
        ev = np.linalg.eig(bmat)[0]
        return np.sort(ev)[-1::-1]


class BCUT(BCUTBase):
    r"""BCUT descriptor.

    :type prop: :py:class:`str` or :py:class:`function`
    :param prop: :ref:`atomic_properties`

    :type nth: int
    :param nth: n-th eigen value. 0 is highest, -1 is lowest.

    :rtype: float
    """

    @classmethod
    def preset(cls):
        return (
            cls(a, n)
            for a in _atomic_property.get_properties(istate=True, charge=True)
            for n in [0, -1]
        )

    @property
    def gasteiger_charges(self):
        return getattr(self.prop, 'gasteiger_charges', False)

    def __str__(self):
        if self.nth < 0:
            return 'BCUT{}-{}l'.format(self.prop_name, np.abs(self.nth))
        else:
            return 'BCUT{}-{}h'.format(self.prop_name, self.nth + 1)

    descriptor_keys = 'prop', 'nth'

    def __init__(self, prop='m', nth=0):
        self.prop_name, self.prop = _atomic_property.getter(prop, self.explicit_hydrogens)
        self.nth = nth

    def dependencies(self):
        return dict(bev=BurdenEigenValues(self.prop, self.gasteiger_charges))

    def calculate(self, mol, bev):
        try:
            return bev[self.nth]
        except IndexError:
            return np.nan
