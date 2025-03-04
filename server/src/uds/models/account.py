# -*- coding: utf-8 -*-
#
# Copyright (c) 2012-2020 Virtual Cable S.L.U.
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
.. moduleauthor:: Adolfo Gómez, dkmaster at dkmon dot com
"""
import logging
import typing

from django.db import models

from .uuid_model import UUIDModel
from .tag import TaggingMixin
from .util import getSqlDatetime
from .util import NEVER

logger = logging.getLogger(__name__)

# Not imported at runtime, just for type checking
if typing.TYPE_CHECKING:
    from uds.models import UserService, AccountUsage


class Account(UUIDModel, TaggingMixin):  # type: ignore
    """
    Account storing on DB model
    """

    name = models.CharField(max_length=128, unique=False, db_index=True)
    time_mark = models.DateTimeField(default=NEVER)
    comments = models.CharField(max_length=256)

    # "fake" declarations for type checking
    objects: 'models.BaseManager[Account]'
    usages: 'models.QuerySet[AccountUsage]'

    def startUsageAccounting(self, userService: 'UserService') -> None:
        if hasattr(userService, 'accounting'):  # Already has an account
            return None

        start = getSqlDatetime()

        if userService.user:
            userName = userService.user.pretty_name
            userUuid = userService.user.uuid
        else:
            userName = '??????'
            userUuid = '00000000-0000-0000-0000-000000000000'

        self.usages.create(
            user_service=userService,
            user_name=userName,
            user_uuid=userUuid,
            pool_name=userService.deployed_service.name,
            pool_uuid=userService.deployed_service.uuid,
            start=start,
            end=start,
        )

    def stopUsageAccounting(self, userService: 'UserService') -> None:
        # if one to one does not exists, attr is not there
        if not hasattr(userService, 'accounting'):
            return

        tmp = userService.accounting
        tmp.user_service = None  # type: ignore
        tmp.end = getSqlDatetime()
        tmp.save()

    class Meta:
        """
        Meta class to declare the name of the table at database
        """

        db_table = 'uds_accounts'
        app_label = 'uds'

    def __str__(self):
        return 'Account id {}, name {}'.format(self.id, self.name)
