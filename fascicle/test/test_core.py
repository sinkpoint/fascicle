#!/usr/bin/env python
import unittest
from fascicle.trkmanage import loadVtk, saveVtk, TrackManager
import shutil
import os

class TestCore(unittest.TestCase):

    def test_vtk_io(self):
        os.chdir('data')
        os.remove('test.tdb')
        os.remove('test.vtp')

        tmgr = TrackManager('test.tdb')
        tmgr.tracts_to_db('C20_xst_cnvR_filtered.vtp', group='0')
        tmgr.tracts_to_db('TN04_xst_cnvL_filtered.vtp', group='1')
        tmgr.to_vtk('test.vtp', merged=True)

        return True





if __name__ == '__main__':
    unittest.main()