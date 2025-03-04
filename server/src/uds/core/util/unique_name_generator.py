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
@author: Adolfo Gómez, dkmaster at dkmon dot com
"""
import logging

from .unique_id_generator import UniqueIDGenerator

logger = logging.getLogger(__name__)


# noinspection PyMethodOverriding
class UniqueNameGenerator(UniqueIDGenerator):
    def __init__(self, owner):
        super().__init__('name', owner)

    def __toName(self, seq: int, length: int) -> str:
        if seq == -1:
            raise KeyError('No more names available. Please, increase service digits.')
        return "%s%0*d" % (self._baseName, length, seq)

    def get(self, baseName: str, length: int = 5) -> str:  # type: ignore  # pylint: disable=arguments-differ
        self.setBaseName(baseName)
        minVal = 0
        maxVal = 10 ** length - 1
        return self.__toName(super().get(minVal, maxVal), length)

    def transfer(self, baseName: str, name: str, toUNGen: 'UniqueNameGenerator'):  # type: ignore # pylint: disable=arguments-differ
        self.setBaseName(baseName)
        super().transfer(int(name[len(self._baseName) :]), toUNGen)

    def free(self, baseName: str, name: str) -> None:  # type: ignore  # pylint: disable=arguments-differ
        self.setBaseName(baseName)
        super().free(int(name[len(self._baseName) :]))
