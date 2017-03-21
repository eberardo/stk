"""
This module defines general-purpose objects, functions and classes.

Functions, classes, etc. defined here should not depend on any other
part of MMEA. They must be completely self-sufficient.

"""

import rdkit.Chem.AllChem as rdkit
from rdkit.Geometry import Point3D
import numpy as np
import time
from contextlib import contextmanager
import os
import subprocess as sp
import gzip
import re
from collections import deque
import shutil
import tarfile
import traceback

# Holds the elements Van der Waals radii in Angstroms.
atom_vdw_radii = {
              'Al': 2, 'Sb': 2, 'Ar': 1.88, 'As': 1.85, 'Ba': 2,
              'Be': 2, 'Bi': 2, 'B': 2, 'Br': 1.85, 'Cd': 1.58,
              'Cs': 2, 'Ca': 2, 'C': 1.7, 'Ce': 2, 'Cl': 1.75,
              'Cr': 2, 'Co': 2, 'Cu': 1.4, 'Dy': 2, 'Er': 2,
              'Eu': 2, 'F':  1.47, 'Gd': 2, 'Ga': 1.87, 'Ge': 2,
              'Au': 1.66, 'Hf': 2, 'He': 1.4, 'Ho': 2, 'H': 1.09,
              'In': 1.93, 'I': 1.98, 'Ir': 2, 'Fe': 2, 'Kr': 2.02,
              'La': 2, 'Pb': 2.02, 'Li': 1.82, 'Lu': 2, 'Mg': 1.73,
              'Mn': 2, 'Hg': 1.55, 'Mo': 2, 'Nd': 2, 'Ne': 1.54,
              'Ni': 1.63, 'Nb': 2, 'N':  1.55, 'Os': 2, 'O':  1.52,
              'Pd': 1.63, 'P': 1.8, 'Pt': 1.72, 'K': 2.75, 'Pr': 2,
              'Pa': 2, 'Re': 2, 'Rh': 2, 'Rb': 2, 'Ru': 2, 'Sm': 2,
              'Sc': 2, 'Se': 1.9, 'Si': 2.1, 'Ag': 1.72, 'Na': 2.27,
              'Sr': 2, 'S': 1.8, 'Ta': 2, 'Te': 2.06, 'Tb': 2,
              'Tl': 1.96, 'Th': 2, 'Tm': 2, 'Sn': 2.17, 'Ti': 2,
              'W': 2, 'U':  1.86, 'V':  2, 'Xe': 2.16, 'Yb': 2,
              'Y': 2, 'Zn': 1.29, 'Zr': 2, 'X':  1.0, 'D':  1.0
                 }

# This dictionary gives easy access to the rdkit bond types.
bond_dict = {'1' : rdkit.rdchem.BondType.SINGLE,
             'am' : rdkit.rdchem.BondType.SINGLE,
             '2' : rdkit.rdchem.BondType.DOUBLE,
             '3' : rdkit.rdchem.BondType.TRIPLE,
             'ar' : rdkit.rdchem.BondType.AROMATIC}

# A dictionary which matches atomic number to elemental symbols.
periodic_table = {
              1: 'H', 2: 'He', 3: 'Li', 4: 'Be', 5: 'B', 6: 'C',
              7: 'N', 8: 'O',  9: 'F', 10: 'Ne', 11: 'Na', 12: 'Mg',
              13: 'Al', 14: 'Si', 15: 'P', 16: 'S', 17: 'Cl',
              18: 'Ar', 19: 'K', 20: 'Ca', 21: 'Sc', 22: 'Ti',
              23: 'V', 24: 'Cr', 25: 'Mn', 26: 'Fe', 27: 'Co',
              28: 'Ni', 29: 'Cu', 30: 'Zn', 31: 'Ga', 32: 'Ge',
              33: 'As', 34: 'Se', 35: 'Br', 36: 'Kr', 37: 'Rb',
              38: 'Sr', 39: 'Y', 40: 'Zr', 41: 'Nb', 42: 'Mo',
              43: 'Tc', 44: 'Ru', 45: 'Rh', 46: 'Pd', 47: 'Ag',
              48: 'Cd', 49: 'In', 50: 'Sn', 51: 'Sb', 52: 'Te',
              53: 'I', 54: 'Xe', 55: 'Cs', 56: 'Ba', 57: 'La',
              58: 'Ce', 59: 'Pr', 60: 'Nd', 61: 'Pm', 62: 'Sm',
              63: 'Eu', 64: 'Gd', 65: 'Tb', 66: 'Dy', 67: 'Ho',
              68: 'Er', 69: 'Tm', 70: 'Yb', 71: 'Lu', 72: 'Hf',
              73: 'Ta', 74: 'W', 75: 'Re', 76: 'Os', 77: 'Ir',
              78: 'Pt', 79: 'Au', 80: 'Hg', 81: 'Tl', 82: 'Pb',
              83: 'Bi', 84: 'Po', 85: 'At', 86: 'Rn', 87: 'Fr',
              88: 'Ra', 89: 'Ac', 90: 'Th', 91: 'Pa', 92: 'U',
              93: 'Np', 94: 'Pu', 95: 'Am', 96: 'Cm', 97: 'Bk',
              98: 'Cf', 99: 'Es', 100: 'Fm', 101: 'Md', 102: 'No',
              103: 'Lr', 104: 'Rf', 105: 'Db', 106: 'Sg', 107: 'Bh',
              108: 'Hs', 109: 'Mt', 110: 'Ds', 111: 'Rg', 112: 'Cn',
              113: 'Uut', 114: 'Fl', 115: 'Uup', 116: 'Lv',
              117: 'Uus', 118: 'Uuo'}


class ChargedMolError(Exception):
    def __init__(self, mol_file, msg):
        self.mol_file = mol_file
        self.msg = msg


class MolError(Exception):
    """
    A class for raising errors when using ``Molecule`` instances.

    There are a lot of reason why MMEA might receive an error. The
    error can originate when rkdit is trying to assembly a molucue,
    sanitize it or manipulate it in some othe way. Equally,
    optimizations may go wrong for one reason or another and raise an
    error.

    However, errors raised by rdkit are not as useful as one would
    hope. The error gets raised but the user is not told which
    ``Molecule`` instance was being manipulated. This makes replication
    of the error difficult.

    In order to address this, all errors should be caught and placed
    into a ``MolError`` along with the Molecule instance on which the
    error occured. On initialization of a MolError an entry is made in
    the file ``failures.txt``. This file is located in the ``output``
    directory. Writing the entry to the file means that a Molecule can
    be easily rebuilt as its building blocks, topology and any other
    parameters are written to this file.

    Every try/except statement in  MMEA should be something like:

        try:
            raise SomeExceptionByRdkit(...)

        except Exception as ex:
            MolError(ex, mol, 'error in init')

            # Do some stuff here. Reraise if you want or pass.

    Notice that though an error is not raised, it is recorded in the
    ``failures.txt`` file. This is because a MolError instance was
    initialized during error handling.

    Attributes
    ----------
    ex : Exception
        The exception raised by some other part of MMEA such as rdkit,
        or MacroModel.

    mol : Molecule
        The Molecule on which the error was raised.

    notes : str
        Any additional comments about the exception. For example, where
        it is being raised.

    """

    def __init__(self, ex, mol, notes):
        self.ex = ex
        self.notes = notes
        self.write_to_file(mol)
        print('\n\nMolError written to ``failures.txt``.\n\n')

    def write_to_file(self, mol):
        """
        Writes the exception and Molecule to ``failures.txt``.

        This method is run during initialization. This means that even
        if an exception is ignored during runtime it will be still
        recorded in the ``failures.txt`` file.

        """

        # If the ``output`` folder exists (such as when running a GA
        # run) place the ``failures.txt`` file in it. If the file does
        # not exist (like when using MMEA as a library) place the
        # ``failures.txt`` in the same folder as ``MMEA``.
        cwd = os.getcwd().split('output')[0]
        if 'output' in os.getcwd():
            name = os.path.join(cwd, 'output', 'failures.txt')
        else:
            name = os.path.join(cwd, 'failures.txt')

        with open(name, 'a') as f:
            f.write("{} - {}\n\n".format(type(self.ex).__name__,
                                            self.ex))

            traceback.print_exc(file=f)

            f.write('\nnote = {}\n'.format(self.notes))

            if hasattr(mol, 'building_blocks'):
                f.write('building blocks = {}\n'.format(
                                                  mol.building_blocks))

                f.write('topology = {}\n'.format(mol.topology))

            f.write('\n'+'='*240)
            f.write('\n\n\n')


class MolFileError(Exception):
    def __init__(self, mol_file, msg):
        self.mol_file = mol_file
        self.msg = msg


class PopulationSizeError(Exception):
    def __init__(self, msg):
        self.msg = msg


class FunctionData:
    """
    Stores information about functions and their parameters.

    Attributes
    ----------
    name : str
        The name of a function or method.

    params : dict
        The parameters of the function or method who's name is held by
        `name`.

    """

    __slots__ = ['name', 'params']

    def __init__(self, name, **kwargs):
        self.name = name
        self.params = kwargs

    def __hash__(self):
        return 1

    def __eq__(self, other):

        same_length = len(self) == len(other)
        same_items = all(x in other.params.items() for x in
                            self.params.items())
        same_name = self.name == other.name

        return same_length and same_items and same_name

    def __len__(self):
        return len(self.params.items())

    def __str__(self):
        s = ", ".join("{}={!r}".format(key, value) for key, value in
                                self.params.items())
        return "FunctionData({!r}, ".format(self.name) + s + ")"

    def __repr__(self):
        return str(self)


class LazyAttr:
    """
    A descriptor for creating lazy attributes.

    """

    def __init__(self, func):
        self.func = func

    def __get__(self, obj, cls):
        if obj is None:
            return self
        val = self.func(obj)
        setattr(obj, self.func.__name__, val)
        return val


class MAEExtractor:
    """
    Extracts the lowest energy conformer from a .maegz file.

    Macromodel conformer searches produce -out.maegz files containing
    all of the conformers found during the search and their energies
    and other data.

    Initializing this class with a MacroMolecule finds that
    MacroMolecules -out.maegz file and converts it to a .mae file. It
    then creates and additional .mae file holding only the lowest
    energy conformer found.

    Attributes
    ----------
    maegz_path : str
        The path to the `-out.maegz` file generated by the macromodel
        conformer search.

    mae_path : str
        The path to the .mae file holding the conformers generated by
        the macromodel conformer search.

    content : str
        The content of the .mae file hodling all the conformers from
        the macromodel conformer search. This holds other data such as
        their energies too.

    energies : list of tuples of (float, int)
        The list holds the id and energy of every conformer in the .mae
        file.

    min_energy : float
        The minimum energy found in the .mae file.

    path : str
        The full path of the .mae file holding the extracted lowest
        energy conformer.

    """

    def __init__(self, file):

        name, ext = os.path.splitext(file)
        self.maegz_path = name + '-out.maegz'
        self.maegz_to_mae()
        self.extract_conformer()

    def extract_conformer(self):
        """
        Creates a .mae file holding the lowest energy conformer.

        """

        # Get the id of the lowest energy conformer.
        num = self.lowest_energy_conformer()

        # Get the structure block corresponding to the lowest energy
        # conformer.
        content = self.content.split("f_m_ct")
        new_mae = "f_m_ct".join([content[0], content[num]])

        # Write the structure block in its own .mae file, named after
        # conformer extracted.
        new_name = self.mae_path.replace('.mae',
                                    '_EXTRACTED_{}.mae'.format(num))
        with open(new_name, 'w') as mae_file:
            mae_file.write(new_mae)

        # Save the path of the newly created file.
        self.path = new_name

    def extract_energy(self, block):
        """
        Extracts the energy value from a .mae energy data block.

        """

        block = block.split(":::")
        for name, value in zip(block[0].split('\n'),
                               block[1].split('\n')):
            if 'r_mmod_Potential_Energy' in name:
                return float(value)

    def lowest_energy_conformer(self):
        """
        Returns the id of the lowest energy conformer in the .mae file.

        """

        # Open the .mae file holding all the conformers and load its
        # content.
        with open(self.mae_path, 'r') as mae_file:
            self.content = mae_file.read()
            # Split the content across curly braces. This divides the
            # various sections of the .mae file.
            content_split = re.split(r"[{}]", self.content)


        # Go through all the datablocks in the the .mae file. For each
        # energy block extract the energy and store it in the
        # `energies` list. Store the `index`  (conformer id) along with
        # each extracted energy.
        self.energies = []
        prev_block = deque([""], maxlen=1)
        index = 1
        for block in content_split:
            if ("f_m_ct" in prev_block[0] and
                                "r_mmod_Potential_Energy" in block):
                energy = self.extract_energy(block)
                self.energies.append((energy, index))
                index += 1

            prev_block.append(block)

        e, conf = min(self.energies)
        self.min_energy = e
        # Return the id of the lowst energy conformer.
        return conf

    def maegz_to_mae(self):
        """
        Converts the .maegz file to a .mae file.

        """

        self.mae_path = self.maegz_path.replace('.maegz', '.mae')
        with gzip.open(self.maegz_path, 'r') as maegz_file:
            with open(self.mae_path, 'wb') as mae_file:
                mae_file.write(maegz_file.read())


def archive_output():
    """
    Places the ``output`` folder into ``old_output``.

    This function assumes that the ``output`` folder is in the current
    working directory.

    Returns
    -------
    None : NoneType

    """

    if 'output' in os.listdir():
        # Make the ``old_output`` folder if it does not exist already.
        if 'old_output' not in os.listdir():
            os.mkdir('old_output')

        # Find out with what number the ``output`` folder should be
        # labelled within ``old_output``.
        num = len(os.listdir('old_output'))
        new_dir = os.path.join('old_output', str(num))
        s = 'Moving old output dir.'
        print('\n'+s + '\n' + '-'*len(s) + '\n\n')
        shutil.copytree('output', new_dir)
        shutil.rmtree('output')


def centroid(*coords):
    """
    Calculates the centroid of a group of coordinates.

    Parameters
    ----------
    *coords : numpy.array
        Any number of numpy arrays holding x, y and z positions.

    Returns
    -------
    numpy.array
        The centroid of the coordinates `coords`.

    """

    total = 0
    for coord in coords:
        total = np.add(total, coord)
    return np.divide(total, len(coords))


def dedupe(iterable, seen=None, key=None):
    """
    Yields items from `iterable` barring duplicates.

    If `seen` is provided it contains elements which are not to be
    yielded at all.

    Parameters
    ----------
    iterable : iterable
        An iterable of elements which are to be yielded, only once.

    seen : set (default = None)
        Holds items which are not to be yielded.

    key : callable
        A function which gets applied to every member of `iterable`.
        The return of this function is checked for duplication rather
        than the member itself.

    Yields
    ------
    object
        Element in `iterable` which is not in `seen` and has not been
        yielded before.

    """

    if seen is None:
        seen = set()
    for x in iterable:
        val = key(x) if key is not None else x
        if val not in seen:
            seen.add(val)
            yield x


def flatten(iterable, excluded_types={str}):
    """
    Transforms an nested iterable into a flat one.

    For example

        [[1,2,3], [[4], [5],[[6]], 7]

    becomes

        [1,2,3,4,5,6,7]

    If a type is found in `excluded_types` it will not be yielded from.
    For example if `str` is in `excluded_types`

        a = ["abcd", ["efgh"]]

    "abcd" and "efgh" are yielded if `a` is passed to `iterable`. If
    `str` was not in `excluded_types` then "a", "b", "c", "d", "e",
    "f", "g" and "h" would all be yielded individually.

    Parameters
    ----------
    iterable : iterable
        The iterable which is to be flattened

    excluded_types : set
        Holds container types which are not be flattened.

    Yields
    ------
    object
        A nested element of `iterable`.

    """

    for x in iterable:
        if hasattr(x, '__iter__') and type(x) not in excluded_types:
            yield from flatten(x)
        else:
            yield x


def kabsch(coords1, coords2):
    """
    Return a rotation matrix to minimize dstance between 2 coord sets.

    This is essentially an implementation of the Kabsch algorithm.
    Given two sets of coordinates, `coords1` and `coords2`, this
    function returns a rotation matrix. When the rotation matrix is
    applied to `coords1` the resulting coordinates have their rms
    distance to `coords2` minimized.

    Parameters
    ----------
    coords1 : numpy.array
        This array represents a matrix hodling coordinates which need
        to be rotated to minimize their rms distance to coordinates in
        `coords2`. The matrix is n x 3. Each row of the matrix holds
        the x, y and z coordinates of one point, respectively. Here
        ``n`` is the number of points.

    coords2 : numpy.array
        This array represents a matrix which holds the coordinates of
        points the distance to which should be minimized. The matrix is
        n x 3. Each row of the matrix holds the x, y and z coordinates
        of one point, respectively. Here ``n`` is the number of points.

    Returns
    -------
    numpy.array
        A rotation matrix. This will be a 3 x 3 matrix.

    References
    ----------
    http://nghiaho.com/?page_id=671
    https://en.wikipedia.org/wiki/Kabsch_algorithm

    """

    h = np.dot(coords1, coords2.T)
    u,s,v = np.linalg.svd(h)

    if int(np.linalg.det(v)) < 0:
        v[:,2] = -v[:,2]

    return np.dot(v, u)


def kill_macromodel():
    """
    Kills any applications left open as a result running MacroModel.

    Applications that are typically left open are
    ``jserver-watcher.exe`` and ``jservergo.exe``.

    Returns
    -------
    None : NoneType

    """

    if os.name == 'nt':
        # In Windows, use the ``Taskkill`` command to force a close on
        # the applications.
        sp.run(["Taskkill", "/IM", "jserver-watcher.exe", "/F"],
               stdout=sp.PIPE, stderr=sp.PIPE)
        sp.run(["Taskkill", "/IM", "jservergo.exe", "/F"],
               stdout=sp.PIPE, stderr=sp.PIPE)

    if os.name == 'posix':
        sp.run(["pkill", "jservergo"],
               stdout=sp.PIPE, stderr=sp.PIPE)
        sp.run(["pkill", "jserver-watcher"],
               stdout=sp.PIPE, stderr=sp.PIPE)


def matrix_centroid(matrix):
    """
    Returns the centroid of the coordinates held in `matrix`.

    Parameters
    ----------
    matrix : np.matrix
        A n x 3 matrix. Each row holds the x, y and z coordinate of
        some point, respectively.

    Returns
    -------
    numpy.array
        A numpy array which holds the x, y and z coordinates of the
        centroid of the coordinates in `matrix`.

    """


    return np.array(np.sum(matrix, axis=0) / len(matrix))[0]


def mol_from_mae_file(mae_path):
    """
    Creates a rdkit molecule from a ``.mae`` file.

    Parameters
    ----------
    mol2_file : str
        The full path of the ``.mae`` file from which an rdkit molecule
        should be instantiated.

    Returns
    -------
    rdkit.Chem.rdchem.Mol
        An rdkit instance of the molecule held in `mae_file`.

    """

    mol = rdkit.EditableMol(rdkit.Mol())
    conf = rdkit.Conformer()

    with open(mae_path, 'r') as mae:
        content = re.split(r'[{}]', mae.read())

    prev_block = deque([''], maxlen=1)
    for block in content:
        if 'm_atom[' in prev_block[0]:
            atom_block = block
        if 'm_bond[' in prev_block[0]:
            bond_block = block
        prev_block.append(block)



    labels, data_block, *_ = atom_block.split(':::')
    labels = [l for l in labels.split('\n') if
               not l.isspace() and l != '']

    data_block = [a.split() for a in data_block.split('\n') if
                   not a.isspace() and a != '']

    for line in data_block:
        line = [word for word in line if word != '"']
        if len(labels) != len(line):
            raise RuntimeError(('Number of labels does'
                      ' not match number of columns in .mae file.'))

        for label, data in zip(labels, line):
            if 'x_coord' in label:
                x = float(data)
            if 'y_coord' in label:
                y = float(data)
            if 'z_coord' in label:
                z = float(data)
            if 'atomic_number' in label:
                atom_num = int(data)

        atom_sym = periodic_table[atom_num]
        atom_coord = Point3D(x,y,z)
        atom_id = mol.AddAtom(rdkit.Atom(atom_sym))
        conf.SetAtomPosition(atom_id, atom_coord)

    labels, data_block, *_ = bond_block.split(':::')
    labels = [l for l in
                labels.split('\n') if not l.isspace() and l != '']
    data_block = [a.split() for a in
                data_block.split('\n') if not a.isspace() and a != '']

    for line in data_block:
        if len(labels) != len(line):
            raise RuntimeError(('Number of labels does'
                      ' not match number of columns in .mae file.'))

        for label, data in zip(labels, line):
            if 'from' in label:
                atom1 = int(data) - 1
            if 'to' in label:
                atom2 = int(data) - 1
            if 'order' in label:
                bond_order = str(int(data))
        mol.AddBond(atom1, atom2, bond_dict[bond_order])

    mol = mol.GetMol()
    mol.AddConformer(conf)
    return mol


def mol_from_mol_file(mol_file):
    """
    Creates a rdkit molecule from a ``.mol`` (V3000) file.

    Parameters
    ----------
    mol_file : str
        The full of the .mol file from which an rdkit molecule should
        be instantiated.

    Returns
    -------
    rdkit.Chem.rdchem.Mol
        An rdkit instance of the molecule held in `mol2_file`.

    Raises
    ------
    ChargedMolError
        If an atom row has more than 8 coloumns it is usually because
        there is a 9th coloumn indicating atomic charge. Such molecules
        are not currently supported, so an error is raised.
    MolFileError
        If the file is not a V3000 .mol file.

    """

    e_mol = rdkit.EditableMol(rdkit.Mol())
    conf = rdkit.Conformer()

    with open(mol_file, 'r') as f:
        take_atom = False
        take_bond = False
        v3000 = False

        for line in f:
            if 'V3000' in line:
                v3000 = True

            if 'M  V30 BEGIN ATOM' in line:
                take_atom = True
                continue

            if 'M  V30 END ATOM' in line:
                take_atom = False
                continue

            if 'M  V30 BEGIN BOND' in line:
                take_bond = True
                continue

            if 'M  V30 END BOND' in line:
                take_bond = False
                continue

            if take_atom:
                words = line.split()
                if len(words) > 8:
                    raise ChargedMolError(mol_file,
                    ('Atom row has more'
                    ' than 8 coloumns. Likely due to a charged atom.'))
                _, _, _, atom_sym, *coords, _ = words
                coords = [float(x) for x in coords]
                atom_coord = Point3D(*coords)
                atom_id = e_mol.AddAtom(rdkit.Atom(atom_sym))
                conf.SetAtomPosition(atom_id, atom_coord)
                continue

            if take_bond:
                *_, bond_id,  bond_order, atom1, atom2 = line.split()
                e_mol.AddBond(int(atom1)-1, int(atom2)-1,
                              bond_dict[bond_order])
                continue
    if not v3000:
        raise MolFileError(mol_file, 'Not a V3000 .mol file.')

    mol = e_mol.GetMol()
    mol.AddConformer(conf)
    return mol


def normalize_vector(vector):
    """
    Normalizes the given vector.

    A new vector is returned, the original vector is not modified.

    Parameters
    ----------
    vector : np.array
        The vector to be normalized.

    Returns
    -------
    np.array
        The normalized vector.

    """

    v = np.divide(vector, np.linalg.norm(vector))
    return np.round(v, decimals=4)


def rotation_matrix(vector1, vector2):
    """
    Returns a rotation matrix which transforms `vector1` to `vector2`.

    Multiplying `vector1` by the rotation matrix returned by this
    function yields `vector2`.

    Parameters
    ----------
    vector1 : numpy.array
        The vector which needs to be transformed to `vector2`.

    vector2 : numpy.array
        The vector onto which `vector1` needs to be transformed.

    Returns
    -------
    numpy.ndarray
        A rotation matrix which transforms `vector1` to `vector2`.

    References
    ----------
    http://tinyurl.com/kybj9ox
    http://tinyurl.com/gn6e8mz

    """

    # Make sure both inputs are unit vectors.
    vector1 = normalize_vector(vector1)
    vector2 = normalize_vector(vector2)

    # Hande the case where the input and output vectors are equal.
    if np.array_equal(vector1, vector2):
        return np.identity(3)

    # Handle the case where the rotation is 180 degrees.
    if np.array_equal(vector1, np.multiply(vector2, -1)):
        # Get a vector orthogonal to `vector1` by finding the smallest
        # component of `vector1` and making that a vector.
        ortho = [0,0,0]
        ortho[list(vector1).index(min(abs(vector1)))] = 1
        axis = np.cross(vector1, ortho)
        return rotation_matrix_arbitrary_axis(np.pi, axis)

    v = np.cross(vector1, vector2)

    vx = np.array([[0, -v[2], v[1]],
                   [v[2], 0, -v[0]],
                   [-v[1], v[0], 0]])

    s = np.linalg.norm(v)
    c = np.dot(vector1, vector2)
    I = np.identity(3)

    mult_factor = (1-c)/np.square(s)

    return I + vx + np.multiply(np.dot(vx,vx), mult_factor)


def rotation_matrix_arbitrary_axis(angle, axis):
    """

    Returns a rotation matrix of `angle` radians about `axis`.

    Parameters
    ----------
    angle : int or float
        The size of the rotation in radians.

    axis : numpy.array
        A 3 element aray which represents a vector. The vector is the
        axis about which the rotation is carried out.

    Returns
    -------
    numpy.array
        A 3x3 array representing a rotation matrix.

    """
    # Calculation of the rotation matrix
    axis = normalize_vector(axis)

    a = np.cos(angle/2)

    b,c,d = np.multiply(axis, np.sin(angle/2))

    e11 = np.square(a) + np.square(b) - np.square(c) - np.square(d)
    e12 = 2*(np.multiply(b,c) - np.multiply(a,d))
    e13 = 2*(np.multiply(b,d) + np.multiply(a,c))

    e21 = 2*(np.multiply(b,c) + np.multiply(a,d))
    e22 = np.square(a) + np.square(c) - np.square(b) - np.square(d)
    e23 = 2*(np.multiply(c,d) - np.multiply(a,b))

    e31 = 2*(np.multiply(b,d) - np.multiply(a,c))
    e32 =  2*(np.multiply(c,d) + np.multiply(a,b))
    e33 = np.square(a) + np.square(d) - np.square(b) - np.square(c)

    return np.array([[e11, e12, e13],
                     [e21, e22, e23],
                     [e31, e32, e33]])


def tar_output():
    """
    Places all the content in the `output` folder into a .tgz file.

    Returns
    -------
    None : NoneType

    """

    tname = os.path.join('output','output.tgz')
    with tarfile.open(tname, 'w:gz') as tar:
        tar.add('output')


@contextmanager
def time_it():
    """
    Times the code executed within the indent.

    This is a context manager so it should be used as:

        with time_it():
            something1()
            something2()
            something3()

    After all 3 functions are finished and the nested block is exited
    the time taken to process the entire block is printed.

    """

    start = time.time()
    yield
    time_taken = time.time() - start
    m,s = divmod(time_taken, 60)
    h,m = divmod(m, 60)
    print('\nTime taken was {} : {} : {}.\n\n'.format(
                                                    int(h), int(m), s))


def vector_theta(vector1, vector2):
    """
    Returns the angle between two vectors in radians.

    Parameters
    ----------
    vector1 : numpy.array
        The first vector.

    vector2 : numpy.array
        The second vector.

    Returns
    -------
    float
        The angle between `vector1` and `vector2` in radians.

    """

    numerator = np.dot(vector1, vector2)
    denominator = (np.linalg.norm(vector1) *
                    np.linalg.norm(vector2))
    # This if statement prevents returns of NaN due to floating point
    # incurracy.
    if np.isclose(numerator, denominator, atol=1e-8):
        return 0.0
    return np.arccos(numerator/denominator)
