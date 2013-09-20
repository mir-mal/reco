import sys
import unittest
import vim
import os
sys.path.append(os.path.abspath('..'))
sys.path.append(os.path.abspath('.'))
import reco as _reco_module
path = "%s/test_files" % os.path.abspath('.')
backup_dir = path
vim.command('set dir=%s' % path)
reco = _reco_module.Reco(backup_dir)
import test_reco_au
suite = unittest.TestLoader().loadTestsFromModule(test_reco_au)
unittest.TextTestRunner(stream=sys.stdout,verbosity=1).run(suite)
