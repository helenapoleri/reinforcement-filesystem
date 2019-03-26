#!/usr/bin/python3
# ------------------------------------------------------------------------------

import os
import sys
import errno
import argparse
import configparser
from fuse import FUSE, FuseOSError, Operations
import time


class Local:


    class __Local:
        def __init__(self, name):

            config = configparser.ConfigParser()
            config.read(os.path.join(os.path.abspath(os.path.dirname(__file__)), '../../config/CONFIGURATION.INI'))

            self.root = config.get(name, 'ROOT')
            self.size = int(config.get(name, 'TOTAL_SPACE'))
            self.delay = int(config.get(name, 'DELAY'))
            self.dict_size = {}
            self.cur_size = 0
            print("CREATING"+ name)

    instance = None

    def __getattr__(self, name):
        return getattr(self.instance, name)

    def __init__(self, name):
        if not Local.instance:
            Local.instance = Local.__Local(name)
            super().__init__()

    # Helpers
    # =======

    def _full_path(self, partial):
        if partial.startswith("/"):
            partial = partial[1:]
        path = os.path.join(self.root, partial)
        return path

    # Filesystem methods
    # ==================

    def get_metadata(self, path, fh=None):
        full_path = self._full_path(path)
        try:
            st = os.lstat(full_path)
            if path != '/'  and not path.endswith('.swp') and not path.endswith('.swx') and not path.endswith('~'):
                self.dict_size[path] = getattr(st,'st_size')
                self.cur_size = sum(self.dict_size.values())
            return {
                    'size': getattr(st,'st_size'),
                    'created': getattr(st,'st_ctime'),
                    'modified': getattr(st,'st_mtime')
                    }
        except Exception:
            return None

    def list_files_names(self):
        return os.listdir(self.root)

    def delete(self, path):
        if path in self.dict_size:
             del self.dict_size[path] 
             self.cur_size = sum(self.dict_size.values())
        return os.unlink(self._full_path(path))

    def move(self, old, new):
        if old in self.dict_size:
             del self.dict_size[old] 
             self.cur_size = sum(self.dict_size.values())
        return os.rename(self._full_path(old), self._full_path(new))

    def open(self, path):
        print("==================OPEN=============")
        time.sleep(self.delay)
        full_path = self._full_path(path)
        return os.open(full_path, 32768)

    def put(self, bytes, path, overwrite=True):
        print("==================PUT=============")
        full= self._full_path(path)
        print(full)
        time.sleep(self.delay)
        full_path = self._full_path(path)
        fh = os.open(full_path, os.O_WRONLY | os.O_CREAT)
        print(type(fh))
        print("FILE DESCRIPTOR " + str(fh))
        return fh

    def read(self, fh, path, length, offset):
        os.lseek(fh, offset, os.SEEK_SET)
        return os.read(fh, length)

    def write(self, path, buf, offset, fh):
        print("==================WRITE=============")
        full= self._full_path(path)
        print(full)
        if not (path.endswith('.swp')):
            buf_len = len(buf)
            new_size = self.cur_size + buf_len
            if  new_size > self.size:
                raise FuseOSError(errno.EACCES)
            else:
                self.dict_size[path] = buf_len
                self.cur_size = new_size
            
        os.lseek(fh, offset, os.SEEK_SET)
        print("WRITE SUCESSO")
        return os.write(fh, buf)

