#!/usr/bin/env python
##
#
# Copyright 2012 Andy Georges
#
# This file is part of the tools originally by the HPC team of
# Ghent University (http://ugent.be/hpc).
#
# This is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation v2.
##
"""Various functions that are missing from the default Python library.

nub(list): keep the unique elements in the list

"""


def nub(list_):
    """Returns the unique items of a list.

    Code is taken from
    http://stackoverflow.com/questions/480214/how-do-you-remove-duplicates-from-a-list-in-python-whilst-preserving-order

    @type list_: a list :-)

    @returns: a new list with each element from `list` appearing only once (cfr. Michelle Dubois).
    """
    seen = set()
    seen_add = seen.add
    return [x for x in list_ if x not in seen and not seen_add(x)]


def find_sublist_index(ls, sub_ls):
    """Find the index at which the sublist sub_ls can be found in ls.

    @type ls: list
    @type sub_ls: list

    @return: index of the matching location or None if no match can be made.
    """
    sub_length = len(sub_ls)
    for i in xrange(len(ls)):
        if ls[i:(i + sub_length)] == sub_ls:
            return i

    return None
