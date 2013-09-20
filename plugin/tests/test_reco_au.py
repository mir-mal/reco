import vim
import unittest
import sys
import os
sys.path.append('.')
import __main__
import re
class Test_reco_auto_commands(unittest.TestCase):
    """Check if each auto command is called correctly, we only check correct
call as all methods are tested separately without auto command.Also we can't
test all autocommand as we can't trigger VimEnter, VimLeave SessionLoad from
within Test_case"""
#TODO filerecovery either create swap and compare content or mock vim.command
#TODO badd_file_recovery same either create swap and compare content or mock 

    @classmethod
    def setUpClass(cls):
        """Set all default values for reco object"""
        __main__.reco._remove_auto_group_reco()

    def setUp(self):
        __main__.reco._add_auto_group_reco()
        vim.command('tabnew!')
    def tearDown(self):
        __main__.reco._remove_auto_group_reco()
        vim.command('tabclose!')
        
    def test_last_buffer_set_name(self):
        """Check if last buffer chanege name successfully"""
        self.assertFalse(vim.current.buffer.name)
        __main__.reco._buf_add_check_last_buffer_name()
        vim.command('new')
        self.assertTrue(vim.current.buffer.name)

    def test_last_buf_with_name(self):
        """If new buffer with name then do nothing"""
        __main__.reco._buf_add_check_last_buffer_name()
        vim.command('file test')
        self.assertTrue(vim.current.buffer.name.endswith('test'))

    def test_check_swapfile_unnamed_set_swapfile_and_nofile(self):
        """Set name to current buffer and check if swapfile and nofile set"""
        name = "%s1.12345" % __main__.reco.buffer_prefix
        __main__.reco.nofile = True
        __main__.reco._buf_win_enter_check_swapfile_au()
        vim.command('new %s' % name)
        self.assertTrue(vim.current.window.buffer.options['swapfile'])
        self.assertTrue(vim.current.window.buffer.options['bt'])
        name = "%s2.12345" % __main__.reco.buffer_prefix
        __main__.reco.nofile = False
        vim.command('new %s' % name)
        self.assertTrue(vim.current.window.buffer.options['swapfile'])
        self.assertFalse(vim.current.window.buffer.options['bt'])

    def test_check_swapfile_set_swapfile_regular_file(self):
        """Set name to current buffer and check if swapfile and nofile set"""
        name = "test_regular"
        vim.current.buffer.name = name
        vim.current.window.buffer.options['swapfile'] = 0
        __main__.reco.check_swapfile()
        self.assertTrue(vim.current.window.buffer.options['swapfile'])

    @unittest.skip("Should be only test if swap exists on hard drive")
    def test_swapcmd_au(self):
        """Check if swap flag on,files exists on disk , noswapfile set and
swapchoice = r """
        __main__.reco._swap_exists_au_for_swapcmd()
        vim.command('new swapcmd_test_file')
        self.assertTrue(__main__.reco.swap_recovered)
        swapfile = int(vim.eval('&swapfile'))
        self.assertFalse(swapfile)
        self.assertTrue(__main__.reco.recovered_cleanup)
        for f in __main__.reco.leave_cleanup:
            self.assertTrue(os.path.exists(\
                os.path.expanduser(f)))
        swapchoice = vim.eval('v:swapchoice')
        self.assertEqual(swapchoice,'r')
        __main__.reco._cleanup(__main__.reco.recovered_cleanup)

    def test_buf_add_check_last_buffer_name_and_set_swapfile(self):
        """Check if added buffer have name set and swapfile set"""
        __main__.reco._buf_add_check_last_buffer_name()
        __main__.reco._buf_win_enter_check_swapfile_au()
        vim.command('new')
        self.assertTrue(vim.current.window.buffer.options['swapfile'])
        __main__.reco.nofile = True
        vim.command('new')
        self.assertTrue(vim.current.window.buffer.options['swapfile'])

    def test_buf_add_increment_buffers_counter(self):
        __main__.reco._buf_add_increment_buffers_counter()
        __main__.reco._vim_entered = True
        old_counter = __main__.reco._buffers_counter
        vim.command('new')
        self.assertEqual(old_counter +1,__main__.reco._buffers_counter)

    def test_buf_unload_decrement_buffers_counter(self):
        __main__.reco._buf_unload_decrement_buffers_counter()
        __main__.reco._vim_entered = True
        vim.command('new')
        old_counter = __main__.reco._buffers_counter
        vim.command('bunload')
        self.assertEqual(old_counter -1,__main__.reco._buffers_counter)

    def test_update_backup_session_all_au(self):
        """To test each event call event , test and delete file"""
        __main__.reco.backup_name = "%s/%s.12345" % (__main__.reco.backup_dir,\
                __main__.reco.backup_prefix)
        __main__.reco._all_au_for_update_backup_session()
        __main__.reco.init_backup = True
        vim.command('new test')
        self.assertTrue(os.path.exists(\
                os.path.expanduser(__main__.reco.backup_name)))
        os.remove(os.path.expanduser(__main__.reco.backup_name))
        self.assertFalse(os.path.exists(\
                os.path.expanduser(__main__.reco.backup_name)))
        vim.command('quit')
        self.assertTrue(os.path.exists(\
                os.path.expanduser(__main__.reco.backup_name)))
        os.remove(os.path.expanduser(__main__.reco.backup_name))
        self.assertFalse(os.path.exists(\
                os.path.expanduser(__main__.reco.backup_name)))
