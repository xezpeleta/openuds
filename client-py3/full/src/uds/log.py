# -*- coding: utf-8 -*-
#
# Copyright (c) 2014-2021 Virtual Cable S.L.U.
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
#    * Neither the name of Virtual Cable S.L. nor the names of its contributors
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

'''
@author: Adolfo Gómez, dkmaster at dkmon dot com
'''
import logging
import os
import os.path
import sys
import tempfile

LOGLEVEL = logging.INFO
DEBUG = False

# Update debug level if uds-debug-on exists
if 'linux' in sys.platform or 'darwin' in sys.platform:
    logFile = os.path.expanduser('~/udsclient.log')
    if os.path.isfile(os.path.expanduser('~/uds-debug-on')):
        LOGLEVEL = logging.DEBUG
        DEBUG = True
else:
    logFile = os.path.join(tempfile.gettempdir(), 'udsclient.log')
    if os.path.isfile(os.path.join(tempfile.gettempdir(), 'uds-debug-on')):
        LOGLEVEL = logging.DEBUG
        DEBUG = True

try:
    logging.basicConfig(
        filename=logFile,
        filemode='a',
        format='%(levelname)s %(asctime)s %(message)s',
        level=LOGLEVEL,
    )
except Exception:
    logging.basicConfig(format='%(levelname)s %(asctime)s %(message)s', level=LOGLEVEL)

logger = logging.getLogger('udsclient')
