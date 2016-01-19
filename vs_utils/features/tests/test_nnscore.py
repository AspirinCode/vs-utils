"""
Test NNScoreComplexFeaturizer.
"""
import os
import unittest
from vs_utils.features.tests import __file__ as test_directory
from vs_utils.features.nnscore import NNScoreComplexFeaturizer

def data_dir():
  """Get location of data directory."""
  return os.path.join(os.path.dirname(test_directory), "data")

class TestNNScoreComplexFeaturizer(unittest.TestCase):
  """
  Test NNScoreComplexFeaturizer.
  """

  def setUp(self):
    """
    Create internal featurizer.
    """
    self.nnscore_featurizer = NNScoreComplexFeaturizer()
    ### 3zso comes from PDBBind-CN
    _3zso_protein_pdb_file = os.path.join(data_dir(), "3zso_protein.pdb")
    with open(_3zso_protein_pdb_file) as f:
      _3zso_protein_pdb = f.readlines()

    # The ligand is also specified by pdbbind
    _3zso_ligand_pdb_file = os.path.join(data_dir(), "3zso_ligand_hyd.pdb")
    with open(_3zso_ligand_pdb_file) as f:
      _3zso_ligand_pdb = f.readlines()

    self.test_cases = [("3zso", _3zso_ligand_pdb, _3zso_protein_pdb)]
    
  def testNNScore(self):
    """
    Run simple tests with NNScore.
    """
    # Currently, just verifies that nothing crashes.
    for test, ligand_pdb, protein_pdb in self.test_cases:
      features = self.nnscore_featurizer.featurize_complexes(
          [ligand_pdb], [protein_pdb])
