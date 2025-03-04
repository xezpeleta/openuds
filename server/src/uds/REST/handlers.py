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
import typing
import logging

from django.contrib.sessions.backends.base import SessionBase
from django.contrib.sessions.backends.db import SessionStore

from uds.core.util.config import GlobalConfig
from uds.core.auths.auth import getRootUser
from uds.core.util import net
from uds.models import Authenticator, User
from uds.core.managers import cryptoManager

# Not imported at runtime, just for type checking
if typing.TYPE_CHECKING:
    from uds.core.util.request import ExtendedHttpRequestWithUser

logger = logging.getLogger(__name__)

AUTH_TOKEN_HEADER = 'HTTP_X_AUTH_TOKEN'


class HandlerError(Exception):
    """
    Generic error for a REST handler
    """


class NotFound(HandlerError):
    """
    Item not found error
    """


class AccessDenied(HandlerError):
    """
    Access denied error
    """


class RequestError(HandlerError):
    """
    Request is invalid error
    """


class ResponseError(HandlerError):
    """
    Generic response error
    """


class NotSupportedError(HandlerError):
    """
    Some elements do not support some operations (as searching over an authenticator that does not supports it)
    """


class Handler:
    """
    REST requests handler base class
    """

    raw: typing.ClassVar[
        bool
    ] = False  # If true, Handler will return directly an HttpResponse Object
    name: typing.ClassVar[
        typing.Optional[str]
    ] = None  # If name is not used, name will be the class name in lower case
    path: typing.ClassVar[
        typing.Optional[str]
    ] = None  # Path for this method, so we can do /auth/login, /auth/logout, /auth/auths in a simple way
    authenticated: typing.ClassVar[
        bool
    ] = True  # By default, all handlers needs authentication. Will be overwriten if needs_admin or needs_staff,
    needs_admin: typing.ClassVar[
        bool
    ] = False  # By default, the methods will be accessible by anyone if nothing else indicated
    needs_staff: typing.ClassVar[bool] = False  # By default, staff

    _request: 'ExtendedHttpRequestWithUser'  # It's a modified HttpRequest
    _path: str
    _operation: str
    _params: typing.Any  # This is a deserliazied object from request. Can be anything as 'a' or {'a': 1} or ....
    _args: typing.Tuple[
        str, ...
    ]  # This are the "path" split by /, that is, the REST invocation arguments
    _kwargs: typing.Dict
    _headers: typing.Dict[str, str]
    _session: typing.Optional[SessionStore]
    _authToken: typing.Optional[str]
    _user: 'User'

    # method names: 'get', 'post', 'put', 'patch', 'delete', 'head', 'options', 'trace'
    def __init__(
        self,
        request: 'ExtendedHttpRequestWithUser',
        path: str,
        operation: str,
        params: typing.Any,
        *args: str,
        **kwargs
    ):

        logger.debug(
            'Data: %s %s %s', self.__class__, self.needs_admin, self.authenticated
        )
        if (
            self.needs_admin or self.needs_staff
        ) and not self.authenticated:  # If needs_admin, must also be authenticated
            raise Exception(
                'class {} is not authenticated but has needs_admin or needs_staff set!!'.format(
                    self.__class__
                )
            )

        self._request = request
        self._path = path
        self._operation = operation
        self._params = params
        self._args = args
        self._kwargs = kwargs
        self._headers = {}
        self._authToken = None
        if (
            self.authenticated
        ):  # Only retrieve auth related data on authenticated handlers
            try:
                self._authToken = self._request.META.get(AUTH_TOKEN_HEADER, '')
                self._session = SessionStore(session_key=self._authToken)
                if 'REST' not in self._session:
                    raise Exception()  # No valid session, so auth_token is also invalid
            except Exception:  # Couldn't authenticate
                self._authToken = None
                self._session = None

            if self._authToken is None:
                raise AccessDenied()

            if self.needs_admin and not self.is_admin():
                raise AccessDenied()

            if self.needs_staff and not self.is_staff_member():
                raise AccessDenied()

            self._user = self.getUser()
        else:
            self._user = User()  # Empty user for non authenticated handlers

    def headers(self) -> typing.Dict[str, str]:
        """
        Returns the headers of the REST request (all)
        """
        return self._headers

    def header(self, headerName: str) -> typing.Optional[str]:
        """
        Get's an specific header name from REST request
        :param headerName: name of header to get
        """
        return self._headers.get(headerName)

    def addHeader(self, header: str, value: str) -> None:
        """
        Inserts a new header inside the headers list
        :param header: name of header to insert
        :param value: value of header
        """
        self._headers[header] = value

    def removeHeader(self, header: str) -> None:
        """
        Removes an specific header from the headers list
        :param header: Name of header to remove
        """
        try:
            del self._headers[header]
        except Exception:
            pass  # If not found, just ignore it

    # Auth related
    def getAuthToken(self) -> typing.Optional[str]:
        """
        Returns the authentication token for this REST request
        """
        return self._authToken

    @staticmethod
    def storeSessionAuthdata(
        session: SessionBase,
        id_auth: int,
        username: str,
        password: str,
        locale: str,
        platform: str,
        is_admin: bool,
        staff_member: bool,
        scrambler: str,
    ):
        """
        Stores the authentication data inside current session
        :param session: session handler (Djano user session object)
        :param id_auth: Authenticator id (DB object id)
        :param username: Name of user (login name)
        :param locale: Assigned locale
        :param is_admin: If user is considered admin or not
        :param staff_member: If is considered as staff member
        """
        if is_admin:
            staff_member = True  # Make admins also staff members :-)

        session['REST'] = {
            'auth': id_auth,
            'username': username,
            'password': cryptoManager().symCrypt(password, scrambler),  # Stores "bytes"
            'locale': locale,
            'platform': platform,
            'is_admin': is_admin,
            'staff_member': staff_member,
        }

    def genAuthToken(
        self,
        id_auth: int,
        username: str,
        password: str,
        locale: str,
        platform: str,
        is_admin: bool,
        staf_member: bool,
        scrambler: str,
    ):
        """
        Generates the authentication token from a session, that is basically
        the session key itself
        :param id_auth: Authenticator id (DB object id)
        :param username: Name of user (login name)
        :param locale: Assigned locale
        :param is_admin: If user is considered admin or not
        :param staf_member: If user is considered staff member or not
        """
        session = SessionStore()
        Handler.storeSessionAuthdata(
            session,
            id_auth,
            username,
            password,
            locale,
            platform,
            is_admin,
            staf_member,
            scrambler,
        )
        session.save()
        self._authToken = session.session_key
        self._session = session

        return self._authToken

    def cleanAuthToken(self) -> None:
        """
        Cleans up the authentication token
        """
        self._authToken = None
        if self._session:
            self._session.delete()
        self._session = None

    # Session related (from auth token)
    def getValue(self, key: str) -> typing.Any:
        """
        Get REST session related value for a key
        """
        try:
            if self._session:
                return self._session['REST'].get(key)
            return None
        except Exception:
            return None

    def setValue(self, key: str, value: typing.Any) -> None:
        """
        Set a session key value
        """
        try:
            if self._session:
                self._session['REST'][key] = value
                self._session.accessed = True
                self._session.save()
        except Exception:
            logger.exception(
                'Got an exception setting session value %s to %s', key, value
            )

    def validSource(self) -> bool:
        try:
            return net.ipInNetwork(
                self._request.ip, GlobalConfig.ADMIN_TRUSTED_SOURCES.get(True)
            )
        except Exception as e:
            logger.warning(
                'Error checking truted ADMIN source: "%s" does not seems to be a valid network string. Using Unrestricted access.',
                GlobalConfig.ADMIN_TRUSTED_SOURCES.get(),
            )

        return True

    def is_admin(self) -> bool:
        """
        True if user of this REST request is administrator and SOURCE is valid admint trusted sources
        """
        return bool(self.getValue('is_admin')) and self.validSource()

    def is_staff_member(self) -> bool:
        """
        True if user of this REST request is member of staff
        """
        return bool(self.getValue('staff_member')) and self.validSource()

    def getUser(self) -> 'User':
        """
        If user is staff member, returns his Associated user on auth
        """
        logger.debug('REST : %s', self._session)
        authId = self.getValue('auth')
        username = self.getValue('username')
        # Maybe it's root user??
        if (
            GlobalConfig.SUPER_USER_ALLOW_WEBACCESS.getBool(True)
            and username == GlobalConfig.SUPER_USER_LOGIN.get(True)
            and authId == -1
        ):
            return getRootUser()
        return Authenticator.objects.get(pk=authId).users.get(name=username)
