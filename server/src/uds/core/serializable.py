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
.. moduleauthor:: Adolfo Gómez, dkmaster at dkmon dot com
"""
import base64
import typing


class Serializable:
    """
    This class represents the interface that all serializable objects must provide.

    Every single serializable class must implement marshall & unmarshall methods. Also, the class must allow
    to be initialized without parameters, so we can:
    - Initialize the object with default values
    - Read values from seralized data
    """

    def __init__(self):
        pass

    def marshal(self) -> bytes:
        """
        This is the method that must be overriden in order to serialize an object.

        The system will use in fact 'seralize' and 'deserialize' methods, but theese are
        only suitable methods to "codify" serialized values

        :note: This method must be overridden
        """
        raise Exception('Base marshaler called!!!')

    def unmarshal(self, data: bytes) -> None:
        """
        This is the method that must be overriden in order to unserialize an object.

        The system will use in fact 'seralize' and 'deserialize' methods, but these are
        only convenients methods to "codify" serialized values.

        Take into account that _str can be '' (empty string), but hopefully it will never be none.
        In that case, initialize the object with default values

        Args:
            data : String readed from persistent storage to deseralilize

        :note: This method must be overridden
        """
        raise Exception('Base unmarshaler called!!!')

    def serialize(self) -> str:
        """
        Serializes and "obfuscates' the data.
        """
        return base64.b64encode(self.marshal()).decode()

    def unserialize(self, data: str) -> None:
        """
        des-obfuscates the data and then de-serializes it via unmarshal method
        """
        self.unmarshal(base64.b64decode(data))
