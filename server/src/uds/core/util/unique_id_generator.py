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
import time
import typing

from django.db import transaction, OperationalError, connection
from django.db.utils import IntegrityError

from uds.models.unique_id import UniqueId
from uds.models.util import getSqlDatetimeAsUnix

if typing.TYPE_CHECKING:
    from django.db import models

logger = logging.getLogger(__name__)

MAX_SEQ = 1000000000000000


class CreateNewIdException(Exception):
    pass


class UniqueIDGenerator:
    _owner: str
    _baseName: str

    def __init__(
        self, typeName: str, owner: str, baseName: typing.Optional[str] = None
    ):
        self._owner = owner + typeName
        self._baseName = 'uds' if baseName is None else baseName

    def setBaseName(self, newBaseName: str):
        self._baseName = newBaseName

    def __filter(
        self, rangeStart: int, rangeEnd: int = MAX_SEQ, forUpdate: bool = False
    ) -> 'models.QuerySet[UniqueId]':
        # Order is defined on UniqueId model, and is '-seq' by default (so this gets items in sequence order)
        # if not for update, do not use the clause :)
        obj = UniqueId.objects.select_for_update() if forUpdate else UniqueId.objects
        return obj.filter(
            basename=self._baseName, seq__gte=rangeStart, seq__lte=rangeEnd
        )

    def get(self, rangeStart: int = 0, rangeEnd: int = MAX_SEQ) -> int:
        """
        Tries to generate a new unique id in the range provided. This unique id
        is global to "unique ids' database
        """
        # First look for a name in the range defined
        stamp = getSqlDatetimeAsUnix()
        seq = rangeStart
        # logger.debug(UniqueId)
        counter = 0
        while True:
            counter += 1
            try:
                # logger.debug('Creating new seq in range {}-{}'.format(rangeStart, rangeEnd))
                with transaction.atomic():
                    flt = self.__filter(rangeStart, rangeEnd, forUpdate=True)
                    try:
                        item = flt.filter(assigned=False).order_by('seq')[0]
                        item.owner = self._owner
                        item.assigned = True
                        item.stamp = stamp
                        item.save()
                        # UniqueId.objects.filter(id=item.id).update(owner=self._owner, assigned=True, stamp=stamp)  # @UndefinedVariable
                        seq = item.seq
                        break
                    except IndexError:  # No free element found
                        item = None

                    # No item was found on first instance (already created, but freed)
                    if not item:
                        # logger.debug('No free found, creating new one')
                        try:
                            last = flt.filter(assigned=True)[
                                0
                            ]  # DB Returns correct order so the 0 item is the last
                            seq = last.seq + 1
                        except IndexError:  # If there is no assigned at database
                            seq = rangeStart
                        # logger.debug('Found seq {0}'.format(seq))
                        if seq > rangeEnd:
                            return -1  # No ids free in range
                        # May ocurr on some circustance that a concurrency access gives same item twice, in this case, we
                        # will get an "duplicate key error",
                        UniqueId.objects.create(
                            owner=self._owner,
                            basename=self._baseName,
                            seq=seq,
                            assigned=True,
                            stamp=stamp,
                        )  # @UndefinedVariable
                        break
            except OperationalError:  # Locked, may ocurr for example on sqlite. We will wait a bit
                # logger.exception('Got database locked')
                if counter % 5 == 0:
                    connection.close()
                time.sleep(1)
            except IntegrityError:  # Concurrent creation, may fail, simply retry
                pass
            except Exception:
                logger.exception('Error')
                return -1

        # logger.debug('Seq: {}'.format(seq))
        return seq

    def transfer(self, seq: int, toUidGen: 'UniqueIDGenerator') -> bool:
        self.__filter(0, forUpdate=True).filter(owner=self._owner, seq=seq).update(
            owner=toUidGen._owner,
            basename=toUidGen._baseName,
            stamp=getSqlDatetimeAsUnix(),  # pylint: disable=protected-access
        )
        return True

    def free(self, seq) -> None:
        logger.debug('Freeing seq %s from %s (%s)', seq, self._owner, self._baseName)
        with transaction.atomic():
            flt = (
                self.__filter(0, forUpdate=True)
                .filter(owner=self._owner, seq=seq)
                .update(owner='', assigned=False, stamp=getSqlDatetimeAsUnix())
            )
        if flt > 0:
            self.__purge()

    def __purge(self) -> None:
        logger.debug('Purging UniqueID database')
        try:
            last = self.__filter(0, forUpdate=False).filter(assigned=True)[0]
            logger.debug('Last: %s', last)
            seq = last.seq + 1
        except Exception:
            # logger.exception('Error here')
            seq = 0
        with transaction.atomic():
            self.__filter(
                seq
            ).delete()  # Clean ups all unassigned after last assigned in this range

    def release(self) -> None:
        UniqueId.objects.select_for_update().filter(owner=self._owner).update(
            assigned=False, owner='', stamp=getSqlDatetimeAsUnix()
        )  # @UndefinedVariable
        self.__purge()

    def releaseOlderThan(self, stamp=None) -> None:
        stamp = getSqlDatetimeAsUnix() if stamp is None else stamp
        UniqueId.objects.select_for_update().filter(
            owner=self._owner, stamp__lt=stamp
        ).update(
            assigned=False, owner='', stamp=stamp
        )  # @UndefinedVariable
        self.__purge()
