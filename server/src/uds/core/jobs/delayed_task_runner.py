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
import time
import codecs
import pickle
import threading
from socket import gethostname
from datetime import timedelta
import logging
import typing

from django.db import connections
from django.db import transaction, OperationalError
from django.db.models import Q

from uds.models import DelayedTask as DBDelayedTask
from uds.models import getSqlDatetime
from uds.core.environment import Environment

from .delayed_task import DelayedTask

logger = logging.getLogger(__name__)


class DelayedTaskThread(threading.Thread):
    """
    Class responsible of executing a delayed task in its own thread
    """

    _taskInstance: DelayedTask

    def __init__(self, taskInstance: DelayedTask) -> None:
        super().__init__()
        self._taskInstance = taskInstance

    def run(self) -> None:
        try:
            self._taskInstance.execute()
        except Exception as e:
            logger.exception("Exception in thread %s: %s", e.__class__, e)
        finally:
            connections['default'].close()


class DelayedTaskRunner:
    """
    Delayed task runner class
    """

    granularity: int = 2  # we check for delayed tasks every "granularity" seconds

    # to keep singleton DelayedTaskRunner
    _runner: typing.ClassVar[typing.Optional['DelayedTaskRunner']] = None
    _hostname: str
    _keepRunning: bool

    def __init__(self):
        self._hostname = gethostname()
        self._keepRunning = True
        logger.debug("Initializing delayed task runner for host %s", self._hostname)

    def notifyTermination(self) -> None:
        """
        Invoke this whenever you want to terminate the delayed task runner thread
        It will mark the thread to "stop" ASAP
        """
        self._keepRunning = False

    @staticmethod
    def runner() -> 'DelayedTaskRunner':
        """
        Static method that returns an instance (singleton instance) to a Delayed Runner.
        There is only one instance of DelayedTaksRunner, but its "run" method is executed on
        many thread (depending on configuration). They all share common Instance data
        """
        if DelayedTaskRunner._runner is None:
            DelayedTaskRunner._runner = DelayedTaskRunner()
        return DelayedTaskRunner._runner

    def executeOneDelayedTask(self) -> None:
        now = getSqlDatetime()
        filt = Q(execution_time__lt=now) | Q(
            insert_date__gt=now + timedelta(seconds=30)
        )
        # If next execution is before now or last execution is in the future (clock changed on this server, we take that task as executable)
        try:
            with transaction.atomic():  # Encloses
                # Throws exception if no delayed task is avilable
                task = (
                    DBDelayedTask.objects.select_for_update()
                    .filter(filt)
                    .order_by('execution_time')[0]
                )  # @UndefinedVariable
                if task.insert_date > now + timedelta(seconds=30):
                    logger.warning(
                        'Executed %s due to insert_date being in the future!', task.type
                    )
                taskInstanceDump = codecs.decode(task.instance.encode(), 'base64')
                task.delete()
            taskInstance = pickle.loads(taskInstanceDump)
        except IndexError:
            return  # No problem, there is no waiting delayed task
        except OperationalError:
            logger.info('Retrying delayed task')
            return
        except Exception:
            # Transaction have been rolled back using the "with atomic", so here just return
            # Note that is taskInstance can't be loaded, this task will not be run
            logger.exception('Obtainint one task for execution')
            return

        if taskInstance:
            logger.debug('Executing delayedTask:>%s<', task)
            taskInstance.env = Environment.getEnvForType(taskInstance.__class__)
            DelayedTaskThread(taskInstance).start()

    def __insert(self, instance: DelayedTask, delay: int, tag: str) -> None:
        now = getSqlDatetime()
        exec_time = now + timedelta(seconds=delay)
        cls = instance.__class__
        instanceDump = codecs.encode(pickle.dumps(instance), 'base64').decode()
        typeName = str(cls.__module__ + '.' + cls.__name__)

        logger.debug(
            'Inserting delayed task %s with %s bytes (%s)',
            typeName,
            len(instanceDump),
            exec_time,
        )

        DBDelayedTask.objects.create(
            type=typeName,
            instance=instanceDump,  # @UndefinedVariable
            insert_date=now,
            execution_delay=delay,
            execution_time=exec_time,
            tag=tag,
        )

    def insert(self, instance: DelayedTask, delay: int, tag: str = '') -> bool:
        retries = 3
        while retries > 0:
            retries -= 1
            try:
                self.__insert(instance, delay, tag)
                break
            except Exception as e:
                logger.info('Exception inserting a delayed task %s: %s', e.__class__, e)
                try:
                    connections['default'].close()
                except Exception:
                    logger.exception('Closing db connection at insert')
                time.sleep(1)  # Wait a bit before next try...
        # If retries == 0, this is a big error
        if retries == 0:
            logger.error(
                "Could not insert delayed task!!!! %s %s %s", instance, delay, tag
            )
            return False
        return True

    def remove(self, tag: str) -> None:
        try:
            with transaction.atomic():
                DBDelayedTask.objects.select_for_update().filter(
                    tag=tag
                ).delete()  # @UndefinedVariable
        except Exception as e:
            logger.exception('Exception removing a delayed task %s: %s', e.__class__, e)

    def checkExists(self, tag: str) -> bool:
        if not tag:
            return False

        try:
            number = DBDelayedTask.objects.filter(tag=tag).count()  # @UndefinedVariable
        except Exception:
            number = 0
            logger.error('Exception looking for a delayed task tag %s', tag)

        return number > 0

    def run(self) -> None:
        logger.debug("At loop")
        while self._keepRunning:
            try:
                time.sleep(self.granularity)
                self.executeOneDelayedTask()
            except Exception as e:
                logger.error('Unexpected exception at run loop %s: %s', e.__class__, e)
                try:
                    connections['default'].close()
                except Exception:
                    logger.exception('Exception clossing connection at delayed task')
        logger.info('Exiting DelayedTask Runner because stop has been requested')
