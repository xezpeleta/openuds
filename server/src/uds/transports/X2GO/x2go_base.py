# -*- coding: utf-8 -*-

#
# Copyright (c) 2016-2019 Virtual Cable S.L.
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
import io
import logging
import typing

import paramiko

from django.utils.translation import ugettext_noop as _, ugettext_lazy
from uds.core.managers import userServiceManager
from uds.core.managers.user_preferences import CommonPrefs
from uds.core.ui import gui
from uds.core import transports
from uds.core.util import os_detector as OsDetector
from uds.core.util import connection

# Not imported at runtime, just for type checking
if typing.TYPE_CHECKING:
    from uds import models

logger = logging.getLogger(__name__)

READY_CACHE_TIMEOUT = 30
SSH_KEY_LENGTH = 1024


class BaseX2GOTransport(transports.Transport):
    """
    Provides access via X2GO to service.
    This transport can use an domain. If username processed by authenticator contains '@', it will split it and left-@-part will be username, and right password
    """

    iconFile = 'x2go.png'
    protocol = transports.protocols.X2GO
    supportedOss = (OsDetector.Linux, OsDetector.Windows)

    fixedName = gui.TextField(
        order=2,
        label=_('Username'),
        tooltip=_('If not empty, this username will be always used as credential'),
        tab=gui.CREDENTIALS_TAB,
    )

    screenSize = gui.ChoiceField(
        label=_('Screen size'),
        order=10,
        tooltip=_('Screen size'),
        defvalue=CommonPrefs.SZ_FULLSCREEN,
        values=[
            {'id': CommonPrefs.SZ_640x480, 'text': '640x480'},
            {'id': CommonPrefs.SZ_800x600, 'text': '800x600'},
            {'id': CommonPrefs.SZ_1024x768, 'text': '1024x768'},
            {'id': CommonPrefs.SZ_1366x768, 'text': '1366x768'},
            {'id': CommonPrefs.SZ_1920x1080, 'text': '1920x1080'},
            {'id': CommonPrefs.SZ_FULLSCREEN, 'text': ugettext_lazy('Full Screen')},
        ],
        tab=gui.PARAMETERS_TAB,
    )

    desktopType = gui.ChoiceField(
        label=_('Desktop'),
        order=11,
        tooltip=_('Desktop session'),
        values=[
            {'id': 'XFCE', 'text': 'Xfce'},
            {'id': 'MATE', 'text': 'Mate'},
            {'id': 'LXDE', 'text': 'Lxde'},
            {'id': 'GNOME', 'text': 'Gnome (see docs)'},
            {'id': 'KDE', 'text': 'Kde (see docs)'},
            # {'id': 'UNITY', 'text': 'Unity (see docs)'},
            {'id': 'gnome-session-cinnamon', 'text': 'Cinnamon 1.4 (see docs)'},
            {'id': 'gnome-session-cinnamon2d', 'text': 'Cinnamon 2.2 (see docs)'},
            {'id': 'UDSVAPP', 'text': 'UDS vAPP'},
        ],
        tab=gui.PARAMETERS_TAB,
    )

    customCmd = gui.TextField(
        order=12,
        label=_('vAPP'),
        tooltip=_(
            'If UDS vAPP is selected as "Desktop", the FULL PATH of the app to be executed. If UDS vAPP is not selected, this field will be ignored.'
        ),
        tab=gui.PARAMETERS_TAB,
    )

    sound = gui.CheckBoxField(
        order=13,
        label=_('Enable sound'),
        tooltip=_('If checked, sound will be available'),
        defvalue=gui.TRUE,
        tab=gui.PARAMETERS_TAB,
    )

    exports = gui.CheckBoxField(
        order=14,
        label=_('Redirect home folder'),
        tooltip=_(
            'If checked, user home folder will be redirected. (On linux, also redirects /media)'
        ),
        defvalue=gui.FALSE,
        tab=gui.PARAMETERS_TAB,
    )

    speed = gui.ChoiceField(
        label=_('Speed'),
        order=15,
        tooltip=_('Connection speed'),
        defvalue='3',
        values=[
            {'id': '0', 'text': 'MODEM'},
            {'id': '1', 'text': 'ISDN'},
            {'id': '2', 'text': 'ADSL'},
            {'id': '3', 'text': 'WAN'},
            {'id': '4', 'text': 'LAN'},
        ],
        tab=gui.PARAMETERS_TAB,
    )

    soundType = gui.ChoiceField(
        label=_('Sound'),
        order=30,
        tooltip=_('Sound server'),
        defvalue='pulse',
        values=[
            {'id': 'pulse', 'text': 'Pulse'},
            {'id': 'esd', 'text': 'ESD'},
        ],
        tab=gui.ADVANCED_TAB,
    )

    keyboardLayout = gui.TextField(
        label=_('Keyboard'),
        order=31,
        tooltip=_('Keyboard layout (es, us, fr, ...). Empty value means autodetect.'),
        defvalue='',
        tab=gui.ADVANCED_TAB,
    )
    # 'nopack', '8', '64', '256', '512', '4k', '32k', '64k', '256k', '2m', '16m'
    # '256-rdp', '256-rdp-compressed', '32k-rdp', '32k-rdp-compressed', '64k-rdp'
    # '64k-rdp-compressed', '16m-rdp', '16m-rdp-compressed'
    # 'rfb-hextile', 'rfb-tight', 'rfb-tight-compressed'
    # '8-tight', '64-tight', '256-tight', '512-tight', '4k-tight', '32k-tight'
    # '64k-tight', '256k-tight', '2m-tight', '16m-tight'
    # '8-jpeg-%', '64-jpeg', '256-jpeg', '512-jpeg', '4k-jpeg', '32k-jpeg'
    # '64k-jpeg', '256k-jpeg', '2m-jpeg', '16m-jpeg-%'
    # '8-png-jpeg-%', '64-png-jpeg', '256-png-jpeg', '512-png-jpeg', '4k-png-jpeg'
    # '32k-png-jpeg', '64k-png-jpeg', '256k-png-jpeg', '2m-png-jpeg', '16m-png-jpeg-%'
    # '8-png-%', '64-png', '256-png', '512-png', '4k-png'
    # '32k-png', '64k-png', '256k-png', '2m-png', '16m-png-%'
    # '16m-rgb-%', '16m-rle-%'
    pack = gui.TextField(
        label=_('Pack'),
        order=32,
        tooltip=_('Pack format. Change with care!'),
        defvalue='16m-jpeg',
        tab=gui.ADVANCED_TAB,
    )

    quality = gui.NumericField(
        label=_('Quality'),
        order=33,
        tooltip=_('Quality value used on some pack formats.'),
        length=1,
        defvalue='6',
        minValue=1,
        maxValue=9,
        required=True,
        tab=gui.ADVANCED_TAB,
    )

    def isAvailableFor(self, userService: 'models.UserService', ip: str) -> bool:
        """
        Checks if the transport is available for the requested destination ip
        Override this in yours transports
        """
        logger.debug('Checking availability for %s', ip)
        ready = self.cache.get(ip)
        if ready is None:
            # Check again for ready
            if connection.testServer(ip, 22):
                self.cache.put(ip, 'Y', READY_CACHE_TIMEOUT)
                return True
            self.cache.put(ip, 'N', READY_CACHE_TIMEOUT)
        return ready == 'Y'

    def getScreenSize(self) -> typing.Tuple[int, int]:
        return CommonPrefs.getWidthHeight(self.screenSize.value)

    def processedUser(
        self, userService: 'models.UserService', user: 'models.User'
    ) -> str:
        v = self.processUserPassword(userService, user, '')
        return v['username']

    def processUserPassword(
        self,
        userService: typing.Union['models.UserService', 'models.ServicePool'],
        user: 'models.User',
        password: str,
    ) -> typing.Dict[str, str]:
        username = user.getUsernameForAuth()

        if self.fixedName.value != '':
            username = self.fixedName.value

        # Fix username/password acording to os manager
        username, password = userService.processUserPassword(username, password)

        return {'protocol': self.protocol, 'username': username, 'password': ''}

    def getConnectionInfo(
        self,
        userService: typing.Union['models.UserService', 'models.ServicePool'],
        user: 'models.User',
        password: str,
    ) -> typing.Dict[str, str]:
        return self.processUserPassword(userService, user, password)

    def genKeyPairForSsh(self) -> typing.Tuple[str, str]:
        """
        Generates a key pair for use with x2go
        The private part is used by client
        the public part must be "appended" to authorized_keys if it is not already added.
        If .ssh folder does not exists, it must be created
        if authorized_keys does not exists, it must be created
        On key adition, we can look for every key that has a "UDS@X2GOCLIENT" as comment, so we can remove them before adding new ones

        Windows (tested):
            C:\\Program Files (x86)\\x2goclient>x2goclient.exe --session-conf=c:/temp/sessions --session=UDS/test-session --close-disconnect --hide --no-menu
        Linux (tested):
            HOME=[temporal folder, where we create a .x2goclient folder and a sessions inside] pyhoca-cli -P UDS/test-session
        """
        key = paramiko.RSAKey.generate(SSH_KEY_LENGTH)
        privFile = io.StringIO()
        key.write_private_key(privFile)
        priv = privFile.getvalue()

        pub = key.get_base64()  # 'ssh-rsa {} UDS@X2GOCLIENT'.format(key.get_base64())
        return priv, pub

    def getAuthorizeScript(self, user: str, pubKey: str) -> str:
        with open(os.path.join(os.path.dirname(__file__), 'scripts/authorize.py')) as f:
            data = f.read()

        return data.replace('__USER__', user).replace('__KEY__', pubKey)

    def getAndPushKey(
        self, userName: str, userService: 'models.UserService'
    ) -> typing.Tuple[str, str]:
        priv, pub = self.genKeyPairForSsh()
        authScript = self.getAuthorizeScript(userName, pub)
        userServiceManager().sendScript(userService, authScript)
        return priv, pub

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
