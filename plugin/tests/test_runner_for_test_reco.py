import sys
import unittest
import vim
import os
sys.path.append(os.path.abspath('..'))
sys.path.append(os.path.abspath('.'))
import test_reco
path = "%s/test_files" % os.path.abspath('.')
vim.command('set dir=%s' % path)
#Backup_dir is set in test_reco module
suite = unittest.TestLoader().loadTestsFromModule(test_reco)
unittest.TextTestRunner(stream=sys.stdout,verbosity=1).run(suite)
