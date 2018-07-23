# Licensed to the StackStorm, Inc ('StackStorm') under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import

from oslo_config import cfg
from jsonschema import ValidationError

from st2common.models.api.trace import TraceContext
from st2common.transport.reactor import TriggerDispatcher
from st2common.validators.api.reactor import validate_trigger_payload

__all__ = [
    'TriggerDispatcherService'
]


class TriggerDispatcherService(object):
    """
    Class for handling dispatching of trigger.
    """

    def __init__(self, logger):
        self._logger = logger
        self._dispatcher = TriggerDispatcher(self._logger)

    def dispatch(self, trigger, payload=None, trace_tag=None):
        """
        Method which dispatches the trigger.

        :param trigger: Full name / reference of the trigger.
        :type trigger: ``str``

        :param payload: Trigger payload.
        :type payload: ``dict``

        :param trace_tag: Tracer to track the triggerinstance.
        :type trace_tags: ``str``
        """
        # empty strings
        trace_context = TraceContext(trace_tag=trace_tag) if trace_tag else None
        self._logger.debug('Added trace_context %s to trigger %s.', trace_context, trigger)
        self.dispatch_with_context(trigger, payload=payload, trace_context=trace_context)

    def dispatch_with_context(self, trigger, payload=None, trace_context=None,
                              validate_payload=None):
        """
        Method which dispatches the trigger.

        :param trigger: Full name / reference of the trigger.
        :type trigger: ``str``

        :param payload: Trigger payload.
        :type payload: ``dict``

        :param trace_context: Trace context to associate with Trigger.
        :type trace_context: ``st2common.api.models.api.trace.TraceContext``

        :param validate_payload: True to validate trigger payload against the trigger schema.
        :type validate_payload: ``boolean``
        """
        if validate_payload is None:
            # If not provided, use a default value from the config
            validate_payload = cfg.CONF.system.validate_trigger_payload

        # Indicates if the provided trigger payload complies with the trigger schema (if one is
        # defined)
        is_valid = True

        try:
            validate_trigger_payload(trigger_type_ref=trigger, payload=payload,
                                     throw_on_inexistent_trigger=True)
        except (ValidationError, Exception) as e:
            is_valid = False
            self._logger.warn('Failed to validate payload (%s) for trigger "%s": %s' %
                              (str(payload), trigger, str(e)))

        # If validation is disabled, still dispatch a trigger even if it failed validation
        # This condition prevents unexpected restriction.
        if not is_valid and validate_payload:
            self._logger.warn('Trigger payload validation failed and validation is enabled, not '
                              'dispatching a trigger "%s" (%s)' % (trigger, str(payload)))
            return None

        self._logger.debug('Dispatching trigger %s with payload %s.', trigger, payload)
        self._dispatcher.dispatch(trigger, payload=payload, trace_context=trace_context)
