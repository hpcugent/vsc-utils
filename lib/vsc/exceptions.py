#!/usr/bin/env python
##
#
# Copyright 2012 Ghent University
# Copyright 2012 Andy Georges
#
# This file is part of the tools originally by the HPC team of
# Ghent University (http://ugent.be/hpc).
#
# This is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation v2.
##
'''Custom exceptions for the VSC Python codebase.

@author Andy Georges

Created April 4, 2012
'''

class VscError(Exception):
    '''Base class for VSC related exceptions.'''
    def __init__(self):
        Exception.__init__(self)


class FileStoreError(VscError):
    '''When something goes wrong when storing data on the file system.'''

    def __init__(self, path, err=None):
        '''Initializer.

        @type path: string indicating the path to the file which was accessed.
        @type err: the original exception.
        '''
        VscError.__init__(self)
        self.path = path
        self.err = err


class FileMoveError(VscError):
    '''When moving a file fails for some reason.'''

    def __init__(self, src, dest, err=None):
        '''Initializer.

        @type src: string indicating the path to the source file.
        @type dest: string indicating the path to the destination file.
        @type err: the original exception, if any.
        '''
        VscError.__init__(self)
        self.src = src
        self.dest = dest
        self.err = err


class FileCopyError(VscError):
    '''When copying a file for some reason.'''

    def __init__(self, src, dest, err=None):
        '''Initializer.

        @type src: string indicating the path to the source file.
        @type dest: string indicating the path to the destination file.
        @type err: the original exception, if any.
        '''
        VscError.__init__(self)
        self.src = src
        self.dest = dest
        self.err = err


class UserStorageError(VscError):
    '''When something goed wrong accessing a user's storage.'''

    def __init__(self, err=None):
        '''Initializer.

        @type err: the original exception, if any.
        '''
        VscError.__init__(self)
        self.err = err