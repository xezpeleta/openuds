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
@author: Adolfo Gómez, dkmaster at dkmon dot com
"""
from datetime import timedelta
import logging

from django.db.models import Q, Count
from uds.core.util.config import GlobalConfig
from uds.models import ServicePool, UserService, getSqlDatetime
from uds.core.util.state import State
from uds.core.jobs import Job
from uds.core.util import log

logger = logging.getLogger(__name__)


class HangedCleaner(Job):
    frecuency = 3601
    frecuency_cfg = GlobalConfig.MAX_INITIALIZING_TIME
    friendly_name = 'Hanged services checker'

    def run(self):
        now = getSqlDatetime()
        since_state = now - timedelta(
            seconds=GlobalConfig.MAX_INITIALIZING_TIME.getInt()
        )
        since_removing = now - timedelta(seconds=GlobalConfig.MAX_REMOVAL_TIME.getInt())
        # Filter for locating machine not ready
        flt = Q(state_date__lt=since_state, state=State.PREPARING) | Q(
            state_date__lt=since_state, state=State.USABLE, os_state=State.PREPARING
        )

        withHangedServices = (
            ServicePool.objects.annotate(
                hanged=Count(
                    'userServices',
                    # Rewrited Filter for servicePool
                    filter=Q(
                        userServices__state_date__lt=since_state,
                        userServices__state=State.PREPARING,
                    )
                    | Q(
                        userServices__state_date__lt=since_state,
                        userServices__state=State.USABLE,
                        userServices__os_state=State.PREPARING,
                    )
                    | Q(
                        userServices__state_date__lt=since_removing,
                        userServices__state=State.REMOVING,
                    ),
                )
            )
            .exclude(hanged=0)
            .exclude(service__provider__maintenance_mode=True)
            .filter(state=State.ACTIVE)
        )

        # Type
        servicePool: ServicePool

        for servicePool in withHangedServices:
            logger.debug('Searching for hanged services for %s', servicePool)
            us: UserService
            for us in servicePool.userServices.filter(flt):
                if us.getProperty(
                    'destroy_after'
                ):  # It's waiting for removal, skip this very specific case
                    continue
                logger.debug('Found hanged service %s', us)
                if (
                    us.state == State.REMOVING
                ):  # Removing too long, remark it as removable
                    log.doLog(
                        us,
                        log.ERROR,
                        'User Service hanged on removal process. Restarting removal.',
                        log.INTERNAL,
                    )
                    log.doLog(
                        servicePool,
                        log.ERROR,
                        'User service {} hanged on removal. Restarting removal.'.format(
                            us.friendly_name
                        ),
                    )
                    us.remove()  # Mark it again as removable, and let's see
                else:
                    log.doLog(
                        us,
                        log.ERROR,
                        'User Service seems to be hanged. Removing it.',
                        log.INTERNAL,
                    )
                    log.doLog(
                        servicePool,
                        log.ERROR,
                        'Removing user service {} because it seems to be hanged'.format(
                            us.friendly_name
                        ),
                    )
                    us.removeOrCancel()
