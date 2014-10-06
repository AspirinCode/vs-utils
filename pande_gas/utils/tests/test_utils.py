"""
Tests for miscellaneous utilities.
"""
import numpy as np
import shutil
import tempfile
import unittest

from rdkit import Chem
from rdkit.Chem import AllChem

from rdkit_utils import serial

from .. import DatasetSharder, pad_array, SmilesMap


class TestDatasetSharder(unittest.TestCase):
    """
    Test DatasetSharder.
    """
    def setUp(self):
        """
        Set up tests.
        """
        self.reader = serial.MolReader()

        # generate molecules
        smiles = ['CC(=O)OC1=CC=CC=C1C(=O)O', 'CC(C)CC1=CC=C(C=C1)C(C)C(=O)O',
                  'CC1=CC=C(C=C1)C2=CC(=NN2C3=CC=C(C=C3)S(=O)(=O)N)C(F)(F)F']
        names = ['aspirin', 'ibuprofen', 'celecoxib']
        self.mols = []
        for s, n in zip(smiles, names):
            mol = Chem.MolFromSmiles(s)
            mol.SetProp('_Name', n)
            AllChem.Compute2DCoords(mol)
            self.mols.append(mol)

        # write molecules to file
        self.temp_dir = tempfile.mkdtemp()
        writer = serial.MolWriter()
        _, self.filename = tempfile.mkstemp(dir=self.temp_dir,
                                            suffix='.sdf.gz')
        with writer.open(self.filename) as w:
            w.write(self.mols)

        self.sharder = DatasetSharder(filename=self.filename,
                                      write_shards=False)
        self.reader = serial.MolReader()

    def tearDown(self):
        """
        Clean up tests.
        """
        shutil.rmtree(self.temp_dir)

    def compare_mols(self, mols, ref_slice=None):
        """
        Compare sharded molecules with original molecules.

        Parameters
        ----------
        mols : iterable
            Molecules to compare to reference molecules.
        ref_slice : slice, optional
            Slice of self.mols to compare with sharded molecules.
        """
        ref_mols = self.mols
        if ref_slice is not None:
            ref_mols = self.mols[ref_slice]
        assert len(mols) == len(ref_mols)
        for a, b in zip(mols, ref_mols):
            assert Chem.MolToSmiles(a) == Chem.MolToSmiles(b)
            assert a.GetProp('_Name') == b.GetProp('_Name')

    def test_shard(self):
        """
        Test DatasetSharder.shard.
        """
        shards = list(self.sharder)
        assert len(shards) == 1
        self.compare_mols(shards[0])

    def test_leftover(self):
        """
        Test sharding when total % chunk_size != 0.
        """
        self.sharder.shard_size = 2
        shards = list(self.sharder)
        assert len(shards) == 2
        assert len(shards[0]) == 2
        self.compare_mols(shards[0], slice(2))
        assert len(shards[1]) == 1
        self.compare_mols(shards[1], slice(2, 3))

    def test_next_filename(self):
        """
        Test DatasetSharder.next_filename.
        """
        self.sharder.prefix = 'foo'
        self.sharder.flavor = 'bar'
        self.sharder.index = 5
        for i in xrange(10):
            assert self.sharder._next_filename() == 'foo-{}.bar'.format(i + 5)

    def test_write_shards(self):
        """
        Test DatasetSharder.write_shard.
        """
        _, prefix = tempfile.mkstemp(dir=self.temp_dir)
        self.sharder.prefix = prefix
        self.sharder.write_shards = True
        self.sharder.flavor = 'sdf.gz'
        self.sharder.shard()
        mols = list(self.reader.open('{}-0.sdf.gz'.format(prefix)))
        self.compare_mols(mols)

    def test_preserve_mol_properties_when_pickling(self):
        """
        Test preservation of molecule properties when pickling.
        """
        _, prefix = tempfile.mkstemp(dir=self.temp_dir)
        self.sharder.prefix = prefix
        self.sharder.write_shards = True
        self.sharder.shard()
        mols = list(self.reader.open('{}-0.pkl.gz'.format(prefix)))
        self.compare_mols(mols)

    def test_guess_prefix(self):
        """
        Test guess_prefix.
        """
        self.sharder = DatasetSharder(filename='../foo.bar.gz')
        assert self.sharder.prefix == 'foo'


class TestMiscUtils(unittest.TestCase):
    """
    Tests for miscellaneous utilities.
    """
    def test_pad_matrix(self):
        """Pad matrix."""
        x = np.random.random((5, 6))
        assert pad_array(x, (10, 12)).shape == (10, 12)
        assert pad_array(x, 10).shape == (10, 10)


class TestSmilesMap(unittest.TestCase):
    """
    Test SmilesMap.
    """
    def setUp(self):
        """
        Set up tests.
        """
        smiles = ['CC(=O)OC1=CC=CC=C1C(=O)O', 'CC(C)CC1=CC=C(C=C1)C(C)C(=O)O',
                  'CC1=CC=C(C=C1)C2=CC(=NN2C3=CC=C(C=C3)S(=O)(=O)N)C(F)(F)F']
        names = ['aspirin', 'ibuprofen', 'celecoxib']
        self.cids = [2244, 3672, 2662]
        self.mols = []
        for s, n in zip(smiles, names):
            mol = Chem.MolFromSmiles(s)
            mol.SetProp('_Name', n)
            self.mols.append(mol)
        self.map = SmilesMap()

    def test_add_mol(self):
        """
        Test SmilesMap.add_mol.
        """
        for mol in self.mols:
            self.map.add_mol(mol)
        smiles_map = self.map.get_map()
        for mol in self.mols:
            assert smiles_map[mol.GetProp('_Name')] == Chem.MolToSmiles(
                mol, isomericSmiles=True)

    def test_add_bare_id(self):
        """
        Test failure when adding bare IDs.
        """
        for mol, cid in zip(self.mols, self.cids):
            mol.SetProp('_Name', str(cid))
        try:
            for mol in self.mols:
                self.map.add_mol(mol)
                raise AssertionError
        except TypeError:
            pass

    def test_add_bare_id_with_prefix(self):
        """
        Test success when adding bare IDs with a prefix set.
        """
        self.map = SmilesMap('CID')
        for mol, cid in zip(self.mols, self.cids):
            mol.SetProp('_Name', str(cid))
        for mol in self.mols:
            self.map.add_mol(mol)
        smiles_map = self.map.get_map()
        for mol in self.mols:
            assert (smiles_map['CID{}'.format(mol.GetProp('_Name'))] ==
                    Chem.MolToSmiles(mol, isomericSmiles=True))

    def test_fail_on_duplicate_id(self):
        """
        Test failure when adding a duplicate ID with a different SMILES string.
        """
        new = Chem.Mol(self.mols[0])
        new.SetProp('_Name', 'celecoxib')
        self.mols.append(new)
        try:
            for mol in self.mols:
                self.map.add_mol(mol)
            raise AssertionError
        except ValueError:
            pass

    def test_fail_on_duplicate_smiles(self):
        """
        Test failure when adding a duplicate SMILES with a different ID.
        """
        self.map = SmilesMap(allow_duplicates=False)
        new = Chem.Mol(self.mols[0])
        new.SetProp('_Name', 'fakedrug')
        self.mols.append(new)
        try:
            for mol in self.mols:
                self.map.add_mol(mol)
            raise AssertionError
        except ValueError:
            pass
