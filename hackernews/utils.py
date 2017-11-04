# howtographql-graphene-tutorial-fixed -- <project>/utils.py
#
# Copyright © 2017 Sean Bolton.
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import logging
import sys
import traceback

from graphql.error import GraphQLError


# ========== graphql-core exception reporting ==========

# Ugh. graphql-core (2.0) unconditionally writes certain exception messages using sys.excepthook[1],
# even when those exceptions are routine happypath GraphQL error returns. This abuse of
# sys.excepthook significantly clutters the console (stderr) output, with information that is only
# rarely useful for debugging, so this provides a means to disable it.
#
# Additionally, graphql-core logs other exceptions[2] without providing a NullHandler for them, so
# unless the call application provides a handler, the messages get handled by the logging.lastResort
# handler[3], which again clutters the logging output. If no handler exists when these tests are
# run, this provides a NullHandler to quiet them.
#
# All of the writes and logging silenced here are redundant, given the information in the exception
# itself, which can be nicely formatted as a string with format_graphql_errors(), below.
#
# [1] graphql/execution/base.py line 90, in ExecutionContext.report_error()
# [2] graphql/execution/executor.py line 313, in resolve_or_error()
# [3] https://docs.python.org/3/library/logging.html#module-level-attributes

logger = None
null_handler = None
saved_excepthook = None

def quiet_graphql():
    """Silence the redundant exception reporting that graphql-core does."""
    def null_excepthook(cls, exc, tb):
        pass
    global logger, null_handler, saved_excepthook
    saved_excepthook = sys.excepthook
    sys.excepthook = null_excepthook
    logger = logging.getLogger('graphql.execution.executor')
    null_handler = None
    if not logger.hasHandlers():
        null_handler = logging.NullHandler()
        logger.addHandler(null_handler)


def unquiet_graphql():
    """Un-silence the graphql-core's redundant exception reporting."""
    global null_handler
    sys.excepthook = saved_excepthook
    if null_handler:
        logger.removeHandler(null_handler)
        null_handler = None


def format_graphql_errors(errors):
    """Return a string with the usual exception traceback, plus some extra fields that GraphQL
    provides.
    """
    if not errors:
        return None
    text = []
    for i, e in enumerate(errors):
        text.append('GraphQL schema execution error [{}]:\n'.format(i))
        if isinstance(e, GraphQLError):
            for attr in ('args', 'locations', 'nodes', 'positions', 'source'):
                if hasattr(e, attr):
                    if attr == 'source':
                        text.append('source: {}:{}\n'
                                    .format(e.source.name, e.source.body))
                    else:
                        text.append('{}: {}\n'.format(attr, repr(getattr(e, attr))))
        if isinstance(e, Exception):
            text.append(''.join(traceback.format_exception(type(e), e, e.stack)))
        else:
            text.append(repr(e) + '\n')
    return ''.join(text)
