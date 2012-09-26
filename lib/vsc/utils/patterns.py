#!/usr/bin/env python
##
#
# Copyright 2012 Andy Georges
#
# This file is part of the tools originally by the HPC team of
# Ghent University (http://hpc.ugent.be).
#
# This is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation v2.
#!/usr/bin/env python
"""
Module offering the Singleton class.


This class can be used as the __metaclass__ class field to ensure only a
single instance of the class gets used in the run of an application or
script.

class A(B):

    __metaclass__ = Singleton

"""


class Singleton(type):
    """Serves as  metaclass for classes that should implement the Singleton pattern.

    See http://stackoverflow.com/questions/6760685/creating-a-singleton-in-python
    """
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]
