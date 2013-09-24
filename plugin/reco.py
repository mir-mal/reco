# ============================================================================
# File:        reco.py
# Description: Reco backup and recovery solution for Vim
# Maintainer:  Mirek Malinowski <malinowski.miroslaw@yahoo.com>
# License:     GPLv2+ -- look it up.
#
# ============================================================================

import os
import vim
import re
import shutil
class Reco(object):
    def __init__(self,backup_dir='~',backup_prefix='reco_backup',\
            buffer_prefix='tmp_buf',nofile = False):
        """(backup_dir,backup_prefix,buffer_prefix,nofile) :
backup_dir -> all backups files and swaps are copied there, all files are
    removed from directory after you quit your vim instance. But still make
    sure that you have enough space
backup_prefix -> all session backups have name <backup_prefix>.<pid> and are
    in backup_dir directory
buffer_prefix -> all unnamed buffers name is <buffer_prefix><buffer_nr>.<pid>
    that name makes them almost unique and allowed as to recover swap for each
    unnamed buffer in session with correct order. Without name for unnamed 
    buffer it was impossible to know which swap belongs to which buffer
nofile -> Set only for unnamed buffers, read more in Vim docs about it. There
    is still swap for all buffers. But if you unload|close window with unnamed
    buffer and nofile = True. Your data from that buffer is gone."""

        self.backup_dir = os.path.abspath(os.path.expanduser(backup_dir))
        self.backup_prefix = backup_prefix
        self.backup_pattern = r'(^[\\a-zA-Z0-9_\./]*%s\.)(\d+)' % \
                self.backup_prefix
        self.backup_name = os.path.expanduser(\
                "%s/%s.%s" % (self.backup_dir,self.backup_prefix,os.getpid()))
        self.init_backup = False
        self.buffer_prefix = buffer_prefix
        self.buffer_pattern = r'(^[\\a-zA-Z0-9_\./]*%s\d+\.)(\d+)' % \
                self.buffer_prefix
        self.nofile = nofile
        self._recovered_swap = None
        self._scratch_buffers_swaps = []
        self._leave_cleanup = []
        self._buffers_counter = 0
        self._unnamed_counter = 1
        self._vim_entered = False
        self._swap_recovered = False
        self._add_au_cmd = 'au Reco %s * :python %s'
        self.setup_auto_commands()

#Only auto-commands have public methods, rest of code should be private and are
#meant to be use only in API
    def check_swapfile(self):
        """Check if swapfile exists for buffer in current window and if unnamed
 buffer also check nofile flag and set if True"""
        match = re.search(self.buffer_pattern,\
                vim.current.window.buffer.name)
        if match:
            vim.current.window.buffer.options['swapfile'] = 1
            if self.nofile:
                vim.current.window.buffer.options['bt'] = 'nofile'
        elif not vim.current.window.buffer.options['swapfile']:
            vim.current.window.buffer.options['swapfile'] = 1

    def check_last_buffer_name(self):
        """Vim always add buffers to the end of buffer list. Check if added
buffer is unnamed if yes set name"""
        last_buf_nr = int(vim.eval('bufnr("$")'))
        buf = vim.buffers[last_buf_nr]
        self._set_name_if_unnamed_buffer(buf)

    def check_filename_after_write(self):
        """When we writing unnamed buffer, set name = filename"""
        match = re.search(self.buffer_pattern,\
                vim.current.window.buffer.name)
        if match:
            last_buf_nr = int(vim.eval('bufnr("$")'))
            vim.current.buffer = vim.buffers[last_buf_nr]

    def vim_enter_buffers_check(self):
        """First set vim_entered flag, then check if session was recovered if
yes do unnamed buffers recovery. After that update unnamed buffers names, set
_buffers_counter and do init_backup for new_session"""
        self._vim_entered = True
        if self._session_recovered():
            self._scratch_buffers_recovery()
            self._update_pid_in_prev_session_buffers()
        self._update_unnamed_buffers()
        self._buffers_counter = len(vim.buffers)
        self._make_init_backup()
       
    def update_backup_session(self):
        """At BufAdd,BufWinEnter,BufWinLeave check if init_backup flag True if
yes update backup as Vim layout might change"""
        if self.init_backup:
            backup_cmd = 'exe "mksession! %s"'
            vim.command(backup_cmd % self.backup_name)

    def vim_leave_buffers_check(self):
        """At VimLeave cleanup all backup files. Also check _buffers_counter
as Vim can call VimLeave auto-cmd for some signals i.e SIGHUP but we must still
treat that as Vim crash. So if Vim call VimLeave check _buffers_counter and if
not positive, Vim unloaded all buffers and its safe to remove backups files.
We not always have counter equal 0 that's why we check if _buffers_counter < 1.
"""
        if self._buffers_counter < 1 and self._leave_cleanup:
            self._cleanup(self._leave_cleanup)

    def increment_buffers_counter(self):
        """At BufAdd, only increment _buffers_counter after vim_enter auto-cmd"""
        if self._vim_entered:
            self._buffers_counter += 1

    def decrement_buffers_counter(self):
        """At BufUnload, only decrement _buffers_counter after vim_enter auto-cmd"""
        if self._vim_entered:
            self._buffers_counter -= 1

    def swapcmd(self):
        """For each SwapExists window, set _swap_recovered flag then make 
copies of swap and if exists file in current state then set v:swapchoice=d to
delete swap file as whole recovery process is done at BufWinEnter"""
        self._swap_recovered = True
        self._copy_file_to_backup_dir()
        self._copy_swapfile_to_backup_dir()
        vim.command('let v:swapchoice = "d"')

    def file_recovery(self):
        """At BufWinEnter check if swap_recovered flag on and do recovery in 
current window and write file if is not unnamed buffer"""
        if self._swap_recovered:
            vim.command('silent! recover! %s' % \
                    self._recovered_swap.replace('%','\%'))
            name = vim.current.buffer.name
            match = re.search(self.buffer_pattern,\
                    vim.current.buffer.name)
            if not match:
                vim.command('write')
            self._swap_recovered = False

    def badd_file_recover(self):
        """At BufAdd check if unnamed buffer added to buffer list, if yes first
check if pid match vim instance pid if not then check for swap and if exists 
copy swap to backup dir then remove swap and add swap from backup dir into 
scratch_buffers_swaps list for recovery"""
        last_buf_nr = int(vim.eval('bufnr("$")'))
        buf = vim.buffers[last_buf_nr]
        match = re.search(self.buffer_pattern,buf.name)
        pid = os.getpid().__str__()
        if not self._vim_entered and match and match.group(2) != pid:
            #get swapfile and move to backup dir and add to recovery
            swapdirs = vim.eval('&dir').split(',')
            for dir in swapdirs:
                if dir is '.':
                    name = "%s/.%s.swp"
                else:
                    name = "%s/%s.swp"
                dir = os.path.abspath(os.path.expanduser(dir))
                buf_name = os.path.basename(buf.name)
                swap = name % (dir,buf_name)
                if os.path.exists(swap):
                    swap_file_path = "%s/%s" % \
                            (os.path.expanduser(self.backup_dir),\
                            swap.replace('/','%'))
                    self._scratch_buffers_swaps.append(\
                            (buf.name,swap_file_path))
                    self._leave_cleanup.append(swap_file_path)
                    shutil.copy2(swap,swap_file_path)
                    os.remove(swap)
                    #break after first swapfile found
                    break

    def diff_swap(self):
        """First check if orginal file exists if yes do diff on file before and
after recovery"""
        file_path = vim.eval('expand("%:p")')
        backup_filename = file_path.replace('/','%')
        backup_file_path = "%s/%s" % (os.path.expanduser(self.backup_dir),\
                backup_filename)
        if os.path.exists(backup_file_path):
            vim.command('silent! tabnew %s' % file_path)
            vim.command('silent! diffsplit %s' % \
                    backup_file_path.replace('%','\%'))
        else:
            print "You can't do diff_swap without file before recovery"

    def before_recovery(self):
        """First check name of file in current window then if exists before
recovery version of that file read that file into current window"""
        backup_filename = vim.current.window.buffer.name.replace('/','%')
        backup_file_path = "%s/%s" % (os.path.expanduser(self.backup_dir),\
                backup_filename)
        if os.path.exists(backup_file_path):
#First delete all text
            vim.command('%d')
#Then read test from backup_file into window
            vim.command('0r %s' % backup_file_path.replace('%','\%'))

#All private methods 
    def _get_new_name(self):
        """Create new name for unnamed buffer"""
        new_name = "%s%s.%s" % (self.buffer_prefix,self._unnamed_counter,\
                os.getpid())
        match = re.search(self.buffer_pattern,new_name)
        if match:
            self._unnamed_counter += 1
            return new_name
        else:
            raise TypeError('new name for unnamed buffer must match patter')

    def _set_name_if_unnamed_buffer(self,buf):
        """Check if buffer is unnamed and we are not loading session now, 
if yes then set new name"""
        if not buf.name and not int(vim.eval('&modified')) and \
                not int(vim.eval("exists('g:SessionLoad')")):
            buf.name = self._get_new_name()

    def _update_unnamed_buffers(self):
        """Loop over buffers and set if no name"""
        for buf in vim.buffers:
            self._set_name_if_unnamed_buffer(buf)

    def _update_pid(self,buf):
        """If buffer from previous session update pid and _buffers_counter 
to match new session"""
        match = re.search(self.buffer_pattern,buf.name)
        if match:
            new_name = "%s%s" % (match.group(1),os.getpid())
            if new_name != buf.name:
                buf.name = new_name
                self._unnamed_counter += 1
                vim.command('bwipeout %s' % match.string)

    def _update_pid_in_prev_session_buffers(self):
        """Update pid part in unnamed buffer name after session recovery"""
        for buf in vim.buffers:
            self._update_pid(buf)

    def _make_init_backup(self):
        """Do init backup and set init_backup flag = True"""
        backup_cmd = 'exe "mksession! %s"'
        vim.command(backup_cmd % self.backup_name)
        if self.backup_name not in self._leave_cleanup:
            self._leave_cleanup.append(self.backup_name)
        self.init_backup = True

    def _cleanup(self,cleanup_list):
        """check if file exists then try to remove each file in cleanup list,
if some of files not exists just print messg in vim but continue."""
        while cleanup_list:
            f = cleanup_list.pop()
            if os.path.exists(os.path.expanduser(f)):
                os.remove(os.path.expanduser(f))

    def _session_recovered(self):
        sess_name = vim.eval('v:this_session')
        match = re.search(self.backup_pattern,sess_name)
        if match:
            os.remove(sess_name)
            return True
        return False

    def _copy_file_to_backup_dir(self):
        """First create backup location path then copy file before recovery"""
        file_path = vim.eval('expand("<afile>:p:h")')
        filename = vim.eval('expand("<afile>:t")')
        full_path = "%s/%s" % (file_path,filename)
        backup_filename = vim.eval(\
                'expand("<afile>:p")').replace('/','%')
        backup_file_path = "%s/%s" % (os.path.expanduser(self.backup_dir),\
                backup_filename)
        if os.path.exists(full_path) and full_path not in self._leave_cleanup:
            self._leave_cleanup.append(backup_file_path)
            shutil.copy2(full_path,backup_file_path)

    def _copy_swapfile_to_backup_dir(self):
        """Create backup_path and copy swapfile there"""
        backup_filename = vim.eval(\
                'expand("<afile>:p")').replace('/','%')
        swapname = vim.eval('v:swapname')
        swap_filename = "%s.swp" % backup_filename
        swap_file_path = "%s/%s" % (os.path.expanduser(self.backup_dir),\
                swap_filename.replace('/','%'))
        if swap_file_path not in self._leave_cleanup:
            self._leave_cleanup.append(swap_file_path)
        self._recovered_swap = swap_file_path
        shutil.copy2(swapname,swap_file_path)

    def _scratch_buffers_recovery(self):
        """Loop over scratch buffers swaps list, pop item and recover"""
        modified = False
        cur_nr = vim.current.buffer.number
        if self._scratch_buffers_swaps and \
            vim.current.buffer.options['modified']:
            vim.current.buffer.options['modified'] = False
            modified = True

        while self._scratch_buffers_swaps:
            name,swap = self._scratch_buffers_swaps.pop()
            for buf in vim.buffers:
                if buf.name == name:
                    nr = buf.number
            vim.current.buffer = vim.buffers[nr]
            vim.command('silent! recover! %s' % swap.replace('%','\%'))
        vim.current.buffer = vim.buffers[cur_nr]
        if modified:
            vim.current.buffer.options['modified'] = True

#All auto-commands functions, they only setup Vim auto-commands and are
#separate for testing only
    def setup_auto_commands(self):
        """Add all auto-commands at once"""
        self._add_auto_group_reco()
        self._buf_add_check_last_buffer_name()
        self._buf_add_increment_buffers_counter()
        self._buf_unload_decrement_buffers_counter()
        self._all_au_for_update_backup_session()
        self._vim_enter_au_for_vim_enter_buffers_check()
        self._vim_leave_au_for_vim_leave_buffers_check()
        self._swap_exists_au_for_swapcmd()
        self._file_recovery_au()
        self._buf_win_enter_check_swapfile_au()
        self._buf_add_file_recover()
        self._buf_write_post_check_filename_after_write()

    def _add_auto_group_reco(self):
        vim.command('augroup Reco')

    def _remove_auto_group_reco(self):
        """Remove whole auto group Reco"""
        vim.command('au! Reco')
    
    def _buf_write_post_check_filename_after_write(self):
        """If unnamed buffer after write set buffer name = filename"""
        vim.command(self._add_au_cmd % \
                ('BufWritePost','reco.check_filename_after_write()'))

    def _buf_add_file_recover(self):
        vim.command(self._add_au_cmd % \
                ('BufAdd','reco.badd_file_recover()'))

    def _buf_add_check_last_buffer_name(self):
        vim.command(self._add_au_cmd % \
                ('BufAdd','reco.check_last_buffer_name()'))

    def _buf_add_increment_buffers_counter(self):
        vim.command(self._add_au_cmd % \
                ('BufAdd','reco.increment_buffers_counter()'))

    def _buf_unload_decrement_buffers_counter(self):
        vim.command(self._add_au_cmd % \
                ('BufUnload','reco.decrement_buffers_counter()'))

    def _all_au_for_update_backup_session(self):
        """Set BufWinEnter,BufWinLeave,BufAdd,BufUnload backup_session au"""
        vim.command(self._add_au_cmd % \
                ('BufAdd,BufWinEnter,BufWinLeave',\
                'reco.update_backup_session()'))

    def _vim_enter_au_for_vim_enter_buffers_check(self):
        vim.command(self._add_au_cmd % \
                ('VimEnter','reco.vim_enter_buffers_check()'))

    def _vim_leave_au_for_vim_leave_buffers_check(self):
        vim.command(self._add_au_cmd % \
                ('VimLeave','reco.vim_leave_buffers_check()'))

    def _swap_exists_au_for_swapcmd(self):
        vim.command('au Reco SwapExists * \
                v:swapcommand = :python reco.swapcmd()')

    def _file_recovery_au(self):
        vim.command(self._add_au_cmd % \
                ('BufWinEnter','reco.file_recovery()'))

    def _buf_win_enter_check_swapfile_au(self):
        vim.command(self._add_au_cmd % \
                ('BufFilePost,BufWinEnter','reco.check_swapfile()'))
