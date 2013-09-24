" ============================================================================
" File:        reco.vim
" Description: Reco backup and recovery solution for Vim
" Maintainer:  Mirek Malinowski <malinowski.miroslaw@yahoo.com>
" License:     GPLv2+ -- look it up.
"
" ============================================================================
let s:path = expand("<sfile>:p:h")
function! Reco()
python << EOF
import sys
import vim
import os
sys.path.append(vim.eval('s:path'))
import reco as _reco_module
backup_dir = "~/.vim/backup" #if not set default backup dir is home folder
backup_prefix = "vim_backup" # backup_name = <backup_prefix>.<pid>
buffer_prefix = "scratch" # buffer_name = <buffer_prefix><buffer_nr>.<pid>
nofile = False # default False , more about buffer types and nofile :help 'bt'
reco = _reco_module.Reco(backup_dir,backup_prefix,buffer_prefix)
EOF
endfunction
call Reco()
