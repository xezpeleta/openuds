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
.. moduleauthor:: Adolfo Gómez, dkmaster at dkmon dot com
"""
import re
import logging
import typing

from django.utils.translation import ugettext_noop as _

from uds.core.transports import protocols
from uds.core.services import Service, types as serviceTypes
from uds.core.util import tools
from uds.core.ui import gui

from .publication import OVirtPublication
from .deployment import OVirtLinkedDeployment
from . import helpers

# Not imported at runtime, just for type checking
if typing.TYPE_CHECKING:
    from .provider import OVirtProvider
    from uds.core import Module

logger = logging.getLogger(__name__)


class OVirtLinkedService(Service):  # pylint: disable=too-many-public-methods
    """
    oVirt Linked clones service. This is based on creating a template from selected vm, and then use it to
    """

    # : Name to show the administrator. This string will be translated BEFORE
    # : sending it to administration interface, so don't forget to
    # : mark it as _ (using ugettext_noop)
    typeName = _('oVirt/RHEV Linked Clone')
    # : Type used internally to identify this provider
    typeType = 'oVirtLinkedService'
    # : Description shown at administration interface for this provider
    typeDescription = _('oVirt Services based on templates and COW (experimental)')
    # : Icon file used as icon for this provider. This string will be translated
    # : BEFORE sending it to administration interface, so don't forget to
    # : mark it as _ (using ugettext_noop)
    iconFile = 'service.png'

    # Functional related data

    # : If the service provides more than 1 "deployed user" (-1 = no limit,
    # : 0 = ???? (do not use it!!!), N = max number to deploy
    maxDeployed = -1
    # : If we need to generate "cache" for this service, so users can access the
    # : provided services faster. Is usesCache is True, you will need also
    # : set publicationType, do take care about that!
    usesCache = True
    # : Tooltip shown to user when this item is pointed at admin interface, none
    # : because we don't use it
    cacheTooltip = _('Number of desired machines to keep running waiting for a user')
    # : If we need to generate a "Level 2" cache for this service (i.e., L1
    # : could be running machines and L2 suspended machines)
    usesCache_L2 = True
    # : Tooltip shown to user when this item is pointed at admin interface, None
    # : also because we don't use it
    cacheTooltip_L2 = _('Number of desired machines to keep suspended waiting for use')

    # : If the service needs a s.o. manager (managers are related to agents
    # : provided by services itselfs, i.e. virtual machines with actors)
    needsManager = True
    # : If true, the system can't do an automatic assignation of a deployed user
    # : service from this service
    mustAssignManually = False
    canReset = True

    # : Types of publications (preparated data for deploys)
    # : In our case, we do no need a publication, so this is None
    publicationType = OVirtPublication
    # : Types of deploys (services in cache and/or assigned to users)
    deployedType = OVirtLinkedDeployment

    allowedProtocols = protocols.GENERIC + (protocols.SPICE,)
    servicesTypeProvided = (serviceTypes.VDI,)

    # Now the form part
    cluster = gui.ChoiceField(
        label=_("Cluster"),
        order=100,
        fills={
            'callbackName': 'ovFillResourcesFromCluster',
            'function': helpers.getResources,
            'parameters': ['cluster', 'ov', 'ev'],
        },
        tooltip=_("Cluster to contain services"),
        required=True,
    )

    datastore = gui.ChoiceField(
        label=_("Datastore Domain"),
        rdonly=False,
        order=101,
        tooltip=_('Datastore domain where to publish and put incrementals'),
        required=True,
    )

    minSpaceGB = gui.NumericField(
        length=3,
        label=_('Reserved Space'),
        defvalue='32',
        minValue=0,
        order=102,
        tooltip=_('Minimal free space in GB'),
        required=True,
    )

    machine = gui.ChoiceField(
        label=_("Base Machine"),
        order=110,
        tooltip=_('Service base machine'),
        tab=_('Machine'),
        required=True,
    )

    memory = gui.NumericField(
        label=_("Memory (Mb)"),
        length=4,
        defvalue=512,
        minValue=0,
        rdonly=False,
        order=111,
        tooltip=_('Memory assigned to machines'),
        tab=_('Machine'),
        required=True,
    )

    memoryGuaranteed = gui.NumericField(
        label=_("Memory Guaranteed (Mb)"),
        length=4,
        defvalue=256,
        minValue=0,
        rdonly=False,
        order=112,
        tooltip=_('Physical memory guaranteed to machines'),
        tab=_('Machine'),
        required=True,
    )

    usb = gui.ChoiceField(
        label=_('USB'),
        rdonly=False,
        order=113,
        tooltip=_('Enable usb redirection for SPICE'),
        values=[
            gui.choiceItem('disabled', 'disabled'),
            gui.choiceItem('native', 'native'),
            # gui.choiceItem('legacy', 'legacy (deprecated)'),
        ],
        tab=_('Machine'),
        defvalue='1',  # Default value is the ID of the choicefield
    )

    display = gui.ChoiceField(
        label=_('Display'),
        rdonly=False,
        order=114,
        tooltip=_('Display type (only for administration purposes)'),
        values=[gui.choiceItem('spice', 'Spice'), gui.choiceItem('vnc', 'Vnc')],
        tab=_('Machine'),
        defvalue='1',  # Default value is the ID of the choicefield
    )
    baseName = gui.TextField(
        label=_('Machine Names'),
        rdonly=False,
        order=115,
        tooltip=_('Base name for clones from this machine'),
        tab=_('Machine'),
        required=True,
    )

    lenName = gui.NumericField(
        length=1,
        label=_('Name Length'),
        defvalue=5,
        order=116,
        tooltip=_('Size of numeric part for the names of these machines'),
        tab=_('Machine'),
        required=True,
    )

    ov = gui.HiddenField(value=None)
    ev = gui.HiddenField(
        value=None
    )  # We need to keep the env so we can instantiate the Provider

    def initialize(self, values: 'Module.ValuesType') -> None:
        """
        We check here form values to see if they are valid.

        Note that we check them throught FROM variables, that already has been
        initialized by __init__ method of base class, before invoking this.
        """
        if values:
            tools.checkValidBasename(self.baseName.value, self.lenName.num())
            if int(self.memory.value) < 256 or int(self.memoryGuaranteed.value) < 256:
                raise Service.ValidationException(
                    _('The minimum allowed memory is 256 Mb')
                )
            if int(self.memoryGuaranteed.value) > int(self.memory.value):
                self.memoryGuaranteed.value = self.memory.value

    def initGui(self) -> None:
        """
        Loads required values inside
        """

        # Here we have to use "default values", cause values aren't used at form initialization
        # This is that value is always '', so if we want to change something, we have to do it
        # at defValue
        self.ov.defValue = self.parent().serialize()
        self.ev.defValue = self.parent().env.key

        machines = self.parent().getMachines()
        vals = []
        for m in machines:
            vals.append(gui.choiceItem(m['id'], m['name']))

        # This is not the same case, values is not the "value" of the field, but
        # the list of values shown because this is a "ChoiceField"
        self.machine.setValues(vals)

        clusters = self.parent().getClusters()
        vals = []
        for c in clusters:
            vals.append(gui.choiceItem(c['id'], c['name']))

        self.cluster.setValues(vals)

    def parent(self) -> 'OVirtProvider':
        return typing.cast('OVirtProvider', super().parent())

    def datastoreHasSpace(self) -> None:
        """Checks if datastore has enough space

        Raises:
            Exception: Raises an Exception if not enough space

        Returns:
            None -- [description]
        """
        # Get storages for that datacenter
        logger.debug('Checking datastore space for %s', self.datastore.value)
        info = self.parent().getStorageInfo(self.datastore.value)
        logger.debug('Datastore Info: %s', info)
        availableGB = info['available'] / (1024 * 1024 * 1024)
        if availableGB < self.minSpaceGB.num():
            raise Exception(
                'Not enough free space available: (Needs at least {0} GB and there is only {1} GB '.format(
                    self.minSpaceGB.num(), availableGB
                )
            )

    def sanitizeVmName(self, name: str) -> str:
        """
        Ovirt only allows machine names with [a-zA-Z0-9_-]
        """
        return re.sub("[^a-zA-Z0-9_-]", "_", name)

    def makeTemplate(self, name: str, comments: str) -> str:
        """
        Invokes makeTemplate from parent provider, completing params

        Args:
            name: Name to assign to template (must be previously "sanitized"
            comments: Comments (UTF-8) to add to template

        Returns:
            template Id of the template created

        Raises an exception if operation fails.
        """

        # Checks datastore size
        # Get storages for that datacenter

        self.datastoreHasSpace()
        return self.parent().makeTemplate(
            name,
            comments,
            self.machine.value,
            self.cluster.value,
            self.datastore.value,
            self.display.value,
        )

    def getTemplateState(self, templateId: str) -> str:
        """
        Invokes getTemplateState from parent provider

        Args:
            templateId: templateId to remove

        Returns nothing

        Raises an exception if operation fails.
        """
        return self.parent().getTemplateState(templateId)

    def deployFromTemplate(self, name: str, comments: str, templateId: str) -> str:
        """
        Deploys a virtual machine on selected cluster from selected template

        Args:
            name: Name (sanitized) of the machine
            comments: Comments for machine
            templateId: Id of the template to deploy from
            displayType: 'vnc' or 'spice'. Display to use ad oVirt admin interface
            memoryMB: Memory requested for machine, in MB
            guaranteedMB: Minimum memory guaranteed for this machine

        Returns:
            Id of the machine being created form template
        """
        logger.debug('Deploying from template %s machine %s', templateId, name)
        self.datastoreHasSpace()
        return self.parent().deployFromTemplate(
            name,
            comments,
            templateId,
            self.cluster.value,
            self.display.value,
            self.usb.value,
            int(self.memory.value),
            int(self.memoryGuaranteed.value),
        )

    def removeTemplate(self, templateId: str) -> None:
        """
        invokes removeTemplate from parent provider
        """
        self.parent().removeTemplate(templateId)

    def getMachineState(self, machineId: str) -> str:
        """
        Invokes getMachineState from parent provider
        (returns if machine is "active" or "inactive"

        Args:
            machineId: If of the machine to get state

        Returns:
            one of this values:
             unassigned, down, up, powering_up, powered_down,
             paused, migrating_from, migrating_to, unknown, not_responding,
             wait_for_launch, reboot_in_progress, saving_state, restoring_state,
             suspended, image_illegal, image_locked or powering_down
             Also can return'unknown' if Machine is not known
        """
        return self.parent().getMachineState(machineId)

    def startMachine(self, machineId: str) -> None:
        """
        Tries to start a machine. No check is done, it is simply requested to oVirt.

        This start also "resume" suspended/paused machines

        Args:
            machineId: Id of the machine

        Returns:
        """
        self.parent().startMachine(machineId)

    def stopMachine(self, machineId: str) -> None:
        """
        Tries to start a machine. No check is done, it is simply requested to oVirt

        Args:
            machineId: Id of the machine

        Returns:
        """
        self.parent().stopMachine(machineId)

    def suspendMachine(self, machineId: str) -> None:
        """
        Tries to start a machine. No check is done, it is simply requested to oVirt

        Args:
            machineId: Id of the machine

        Returns:
        """
        self.parent().suspendMachine(machineId)

    def removeMachine(self, machineId: str) -> None:
        """
        Tries to delete a machine. No check is done, it is simply requested to oVirt

        Args:
            machineId: Id of the machine

        Returns:
        """
        self.parent().removeMachine(machineId)

    def updateMachineMac(self, machineId: str, macAddres: str) -> None:
        """
        Changes the mac address of first nic of the machine to the one specified
        """
        self.parent().updateMachineMac(machineId, macAddres)

    def fixUsb(self, machineId: str):
        if self.usb.value in ('native',):
            self.parent().fixUsb(machineId)

    def getMacRange(self) -> str:
        """
        Returns de selected mac range
        """
        return self.parent().getMacRange()

    def getBaseName(self) -> str:
        """
        Returns the base name
        """
        return self.baseName.value

    def getLenName(self) -> int:
        """
        Returns the length of numbers part
        """
        return int(self.lenName.value)

    def getDisplay(self) -> str:
        """
        Returns the selected display type (for created machines, for administration
        """
        return self.display.value

    def getConsoleConnection(
        self, machineId: str
    ) -> typing.Optional[typing.MutableMapping[str, typing.Any]]:
        return self.parent().getConsoleConnection(machineId)
