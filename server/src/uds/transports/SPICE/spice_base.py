# -*- coding: utf-8 -*-

#
# Copyright (c) 2012-2019 Virtual Cable S.L.
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

"""
@author: Adolfo Gómez, dkmaster at dkmon dot com
"""
import os
import logging
import typing

from django.utils.translation import ugettext_noop as _
from uds.core.ui import gui
from uds.core import transports
from uds.core.transports import protocols

# Not imported at runtime, just for type checking
if typing.TYPE_CHECKING:
    from uds import models
    from django.http import HttpRequest  # pylint: disable=ungrouped-imports

logger = logging.getLogger(__name__)

READY_CACHE_TIMEOUT = 30


class BaseSpiceTransport(transports.Transport):
    """
    Provides access via SPICE to service.
    This transport can use an domain. If username processed by authenticator contains '@', it will split it and left-@-part will be username, and right password
    """

    iconFile = 'spice.png'
    protocol = protocols.SPICE

    useEmptyCreds = gui.CheckBoxField(
        order=1,
        label=_('Empty credentials'),
        tooltip=_('If checked, the credentials used to connect will be emtpy'),
        tab=gui.CREDENTIALS_TAB,
    )
    fixedName = gui.TextField(
        order=2,
        label=_('Username'),
        tooltip=_('If not empty, this username will be always used as credential'),
        tab=gui.CREDENTIALS_TAB,
    )
    fixedPassword = gui.PasswordField(
        order=3,
        label=_('Password'),
        tooltip=_('If not empty, this password will be always used as credential'),
        tab=gui.CREDENTIALS_TAB,
    )
    serverCertificate = gui.TextField(
        order=4,
        length=4096,
        multiline=4,
        label=_('Certificate'),
        tooltip=_(
            'Server certificate (public), can be found on your ovirt engine, probably at /etc/pki/ovirt-engine/certs/ca.der (Use the contents of this file).'
        ),
        required=False,
    )
    fullScreen = gui.CheckBoxField(
        order=5,
        label=_('Fullscreen Mode'),
        tooltip=_('If checked, viewer will be shown on fullscreen mode-'),
        tab=gui.ADVANCED_TAB,
    )
    smartCardRedirect = gui.CheckBoxField(
        order=6,
        label=_('Smartcard Redirect'),
        tooltip=_('If checked, SPICE protocol will allow smartcard redirection.'),
        defvalue=gui.FALSE,
        tab=gui.ADVANCED_TAB,
    )
    usbShare = gui.CheckBoxField(
        order=7,
        label=_('Enable USB'),
        tooltip=_('If checked, USB redirection will be allowed.'),
        defvalue=gui.FALSE,
        tab=gui.ADVANCED_TAB,
    )
    autoNewUsbShare = gui.CheckBoxField(
        order=8,
        label=_('New USB Auto Sharing'),
        tooltip=_('Auto-redirect USB devices when plugged in.'),
        defvalue=gui.FALSE,
        tab=gui.ADVANCED_TAB,
    )

    def isAvailableFor(self, userService: 'models.UserService', ip: str) -> bool:
        """
        Checks if the transport is available for the requested destination ip
        """
        ready = self.cache.get(ip)
        if ready is None:
            userServiceInstance: typing.Any = (
                userService.getInstance()
            )  # Disable mypy checks on this
            con = userServiceInstance.getConsoleConnection()

            logger.debug('Connection data: %s', con)

            if con is None:
                return False

            port, secure_port = con['port'] or -1, con['secure_port'] or -1

            # test ANY of the ports
            port_to_test = port if port != -1 else secure_port
            if port_to_test == -1:
                self.cache.put(
                    'cachedMsg', 'Could not find the PORT for connection', 120
                )  # Write a message, that will be used from getCustom
                logger.info('SPICE didn\'t find has any port: %s', con)
                return False

            self.cache.put(
                'cachedMsg',
                'Could not reach server "{}" on port "{}" from broker (prob. causes are name resolution & firewall rules)'.format(
                    con['address'], port_to_test
                ),
                120,
            )

            if self.testServer(userService, con['address'], port_to_test) is True:
                self.cache.put(ip, 'Y', READY_CACHE_TIMEOUT)
                ready = 'Y'

        return ready == 'Y'

    def getCustomAvailableErrorMsg(
        self, userService: 'models.UserService', ip: str
    ) -> str:
        msg = self.cache.get('cachedMsg')
        if msg is None:
            return transports.Transport.getCustomAvailableErrorMsg(
                self, userService, ip
            )
        return msg

    def processedUser(
        self, userService: 'models.UserService', user: 'models.User'
    ) -> str:
        v = self.processUserPassword(userService, user, '')
        return v['username']

    def processUserPassword(
        self, userService: typing.Union['models.UserService', 'models.ServicePool'], user: 'models.User', password: str
    ) -> typing.Dict[str, str]:
        username = user.getUsernameForAuth()

        if self.fixedName.value:
            username = self.fixedName.value

        if self.fixedPassword.value:
            password = self.fixedPassword.value

        if self.useEmptyCreds.isTrue():
            username, password = '', ''

        # Fix username/password acording to os manager
        username, password = userService.processUserPassword(username, password)

        return {'protocol': self.protocol, 'username': username, 'password': password}

    def getConnectionInfo(
        self,
        userService: typing.Union['models.UserService', 'models.ServicePool'],
        user: 'models.User',
        password: str,
    ) -> typing.Dict[str, str]:
        return self.processUserPassword(userService, user, password)

    def getScript(
        self, scriptNameTemplate: str, osName: str, params: typing.Dict[str, typing.Any]
    ) -> typing.Tuple[str, str, typing.Dict[str, typing.Any]]:
        # Reads script
        scriptNameTemplate = scriptNameTemplate.format(osName)
        with open(os.path.join(os.path.dirname(__file__), scriptNameTemplate)) as f:
            script = f.read()
        # Reads signature
        with open(
            os.path.join(os.path.dirname(__file__), scriptNameTemplate + '.signature')
        ) as f:
            signature = f.read()
        return script, signature, params
