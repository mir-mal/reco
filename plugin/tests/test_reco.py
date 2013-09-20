import vim
import unittest
import sys
import os
sys.path.append(os.path.abspath('..'))
sys.path.append(os.path.abspath('.'))
import reco
import re
class Test_reco_methods_only(unittest.TestCase):
    """Test all methods and flags but no auto commands """
    @classmethod
    def setUpClass(cls):
        """Set all default values for reco object"""
        backup_dir = "./test_files"
        cls.reco = reco.Reco(backup_dir)
        cls.reco._remove_auto_group_reco()
    def setUp(self):
        vim.command('tabnew')

    def tearDown(self):
        vim.command('tabclose')

    def test_get_new_name_uniqe(self):
        """Check if names are increment and uniqe"""
        name1 = self.reco._get_new_name()
        name2 = self.reco._get_new_name()
        self.assertNotEqual(name1,name2)

    def test_unnamed_buffer_set_name(self):
        """Check if unnamed buffer change name successfully"""
        self.assertFalse(vim.current.buffer.name)
        self.reco._set_name_if_unnamed_buffer(vim.current.buffer)
        self.assertTrue(vim.current.buffer.name)

    def test_buf_with_name(self):
        """If buffer has name then do nothing"""
        vim.command('file test')
        self.reco._set_name_if_unnamed_buffer(vim.current.buffer)
        self.assertTrue(vim.current.buffer.name.endswith('test'))

    def test_update_unnamed_buffers(self):
        """Loop over all bufers and check if each have name set"""
        self.reco._update_unnamed_buffers()
        for buf in vim.buffers:
            self.assertTrue(buf.name)

    def test_update_pid(self):
        """Add buffer with name to be updated, then check if counter is 1up"""
        vim.command('badd %s1.12345' % self.reco.buffer_prefix)
        last_buf_nr = int(vim.eval('bufnr("$")'))
        buf = vim.buffers[last_buf_nr]
        old_counter = self.reco._unnamed_counter
        self.reco._update_pid(buf)
        self.assertEqual(old_counter +1,self.reco._unnamed_counter)

    def test_update_pid_in_prev_session_buffers(self):
        """Add buffer with name to be updated, then check if counter is 1up"""
        vim.command('badd %s1.12345' % self.reco.buffer_prefix)
        old_counter = self.reco._unnamed_counter
        self.reco._update_pid_in_prev_session_buffers()
        self.assertNotEqual(old_counter,self.reco._unnamed_counter)

    def test_if_no_prev_session_buffers_do_nothing(self):
        """Check if no buffers have diffrent pid then current do nothing"""
        old_counter = self.reco._unnamed_counter
        self.reco._update_pid_in_prev_session_buffers()
        self.assertEqual(old_counter,self.reco._unnamed_counter)

    def test_make_init_backup(self):
        """Check if backup file exists and if init_backup flag set"""
        old_backup_name = self.reco.backup_name
        self.reco.backup_name = "~/test_reco_backup.vim"
        self.reco._make_init_backup()
        self.assertTrue(os.path.exists(\
                os.path.expanduser(self.reco.backup_name)))
        os.remove(os.path.expanduser(self.reco.backup_name))
        self.assertFalse(os.path.exists(\
                os.path.expanduser(self.reco.backup_name)))
        self.assertTrue(self.reco.init_backup)
        #restore backup_name
        self.reco.backup_name = old_backup_name

    def test_cleanup(self):
        """Test if files removed from disk and list is empty afterwards"""
        filename = "%s/test_cleanup" % self.reco.backup_dir
        test_file = open(filename,mode="w")
        test_file.close()
        fake_list = [filename]
        self.assertTrue(os.path.exists(\
                os.path.expanduser(filename)))
        self.reco._cleanup(fake_list)
        self.assertFalse(fake_list)
        self.assertFalse(os.path.exists(\
                os.path.expanduser(filename)))

    def test_cleanup_empty_list_and_file_not_exists(self):
        """If empty list do nothing, if some of files not exists still pop
them out from list and check if list is empty"""
        fake_list = []
        self.reco._cleanup(fake_list)
        fake_list.append("no_such/file")
        self.reco._cleanup(fake_list)
        self.assertFalse(fake_list)

    def test_session_recovered_true(self):
        """If session name match backup_pattern remove file and return True"""
        filename = "%s/%s.12345" % (self.reco.backup_dir,\
                self.reco.backup_prefix)
        vim.command('let v:this_session = "%s"' % filename)
        test_file = open(filename,mode="w")
        test_file.close()
        self.assertTrue(self.reco._session_recovered())
        self.assertFalse(os.path.exists(\
                os.path.expanduser(filename)))
        #set this_session empty
        vim.command('let v:this_session = ""')

    def test_session_recovered_flase(self):
        """If session name not match backup_pattern return False"""
        filename = "fake_session"
        vim.command('let v:this_session = "%s"' % filename)
        self.assertFalse(self.reco._session_recovered())
        #set this_session empty
        vim.command('let v:this_session = ""')

#We can't test _copy_file_to_backup_dir and _copy_swapfile_to_backup_dir
#without either auto-command trigger or mocking vim.eval. But both are tested
#with swapcmd in auto-commands test_file. So ignore them as they only eval
#filename and copy them to backup_dir and add to cleanup list

#TODO _scratch_buffers_recovery
#_scratch_buffers_recovery is well checked but do test_file and swapfile and
#write test_case later

#TODO diff_swap,before_recovery are well checked and we don't have time to
#write them, but diff_swap call and check if new tab is open and have 2 bufs
#before recovery check content of buffer before and after recovery
#with diff_swap we could write private methods which accept 2 names of buffers
#to diff.

