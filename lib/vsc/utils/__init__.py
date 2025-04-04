#
# Copyright 2015-2025 Ghent University
#
# This file is part of vsc-utils,
# originally created by the HPC team of Ghent University (http://ugent.be/hpc/en),
# with support of Ghent University (http://ugent.be/hpc),
# the Flemish Supercomputer Centre (VSC) (https://www.vscentrum.be),
# the Flemish Research Foundation (FWO) (http://www.fwo.be/en)
# and the Department of Economy, Science and Innovation (EWI) (http://www.ewi-vlaanderen.be/en).
#
# https://github.com/hpcugent/vsc-utils
#
# vsc-utils is free software: you can redistribute it and/or modify
# it under the terms of the GNU Library General Public License as
# published by the Free Software Foundation, either version 2 of
# the License, or (at your option) any later version.
#
# vsc-utils is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Library General Public License for more details.
#
# You should have received a copy of the GNU Library General Public License
# along with vsc-utils. If not, see <http://www.gnu.org/licenses/>.
#
"""
Allow other packages to extend this namespace, zip safe setuptools style
"""
import pkg_resources
pkg_resources.declare_namespace(__name__)

import os
import warnings
from functools import wraps

def _script_name(full_name):
    """Return the script name without .py extension if any. This assumes that the script name does not contain a
    dot in case of lacking an extension.
    """
    (name, _) = os.path.splitext(full_name)
    return os.path.basename(name)


def deprecated_class(message=None):
    def decorator(cls):
        class Wrapped(cls):
            def __init__(self, *args, **kwargs):
                warnings.warn(
                    f"{cls.__name__} is deprecated. {message or ''}",
                    category=DeprecationWarning,
                    stacklevel=2,
                )
                super().__init__(*args, **kwargs)
        Wrapped.__name__ = cls.__name__
        Wrapped.__doc__ = cls.__doc__
        Wrapped.__module__ = cls.__module__
        return Wrapped
    return decorator
