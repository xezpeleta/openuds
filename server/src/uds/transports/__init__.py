# -*- coding: utf-8 -*-

#
# Copyright (c) 2012-2021 Virtual Cable S.L.U.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
#    * Redistributions of source code must retain the above copyright notice,
#      this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright notice,
#      this list of conditions and the following disclaimer in the documentation
#      and/or other materials provided with the distribution.
#    * Neither the name of Virtual Cable S.L.U. nor the names of its contributors
#      may be used to endorse or promote products derived from this software
#      without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""
Transport modules for UDS are contained inside this package.
To create a new transport module, you will need to follow this steps:
    1.- Create the transport module, probably based on an existing one
    2.- Insert the module package as child of this package
    3.- Import the class of your transport module at __init__. For example::
        from Transport import SimpleTransport
    4.- Done. At Server restart, the module will be recognized, loaded and treated

The registration of modules is done locating subclases of :py:class:`uds.core.auths.Authentication`

.. moduleauthor:: Adolfo Gómez, dkmaster at dkmon dot com
"""
import os.path
import pkgutil
import importlib
import logging
import sys

logger = logging.getLogger(__name__)


def __init__():
    """
    This imports all packages that are descendant of this package, and, after that,
    it register all subclases of service provider as
    """
    from uds.core import transports

    # Dinamycally import children of this package. The __init__.py files of each module must import classes so they can get registered
    pkgpath = os.path.dirname(sys.modules[__name__].__file__)
    for _, name, _ in pkgutil.iter_modules([pkgpath]):
        # __import__(name, globals(), locals(), [], 1)
        importlib.import_module('.' + name, __name__)  # import module

    importlib.invalidate_caches()

    # This is marked as error in IDE, but it's not (__subclasses__)
    for cls in transports.Transport.__subclasses__():
        clsSubCls = cls.__subclasses__()
        if len(clsSubCls) == 0:
            transports.factory().insert(cls)
        else:
            for l2 in clsSubCls:
                transports.factory().insert(l2)


__init__()
