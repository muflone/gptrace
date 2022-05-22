##
#     Project: gpTrace
# Description: Trace the activities of an external application
#      Author: Fabio Castelli (Muflone) <muflone@muflone.com>
#   Copyright: 2014-2022 Fabio Castelli
#     License: GPL-3+
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.
##

from grp import getgrgid
from pwd import getpwuid

from ptrace.debugger.child import ChildError
from ptrace.debugger.process_event import (NewProcessEvent,
                                           ProcessExecution,
                                           ProcessExit)
from ptrace.debugger.ptrace_signal import ProcessSignal
from ptrace.os_tools import RUNNING_LINUX

from gptrace.functions import _

if RUNNING_LINUX:
    from ptrace.linux_proc import readProcessCmdline, readProcessLink, openProc

UID = 'uid'
GID = 'gid'
EUID = 'euid'
EGID = 'egid'


class EventTracer(object):
    def __init__(self, callback):
        """Handle events requests by firing up the callback each time a new
        information must be shown"""
        self.event_callback = callback

    def handle_event(self, event):
        """Handle external events like new process execution or child close"""
        if isinstance(event, NewProcessEvent):
            # Under Linux the new process phase first fork a new process with
            # the same command line of the starting process then changes its
            # command line
            # Therefore here I skip the NewProcessEvent event and after I add
            # a new process during the ProcessExecution event
            status = None
        elif isinstance(event, ProcessExecution):
            status = _('Process execution')
        elif isinstance(event, ProcessExit):
            status = _('Process exit')
        elif isinstance(event, ProcessSignal):
            status = _('Process signal: %s') % event
        elif isinstance(event, ChildError):
            status = None
            print(event)
        else:
            status = _('Event: %s') % event

        if status:
            pid = event.process.pid
            if RUNNING_LINUX and isinstance(event, ProcessExecution):
                self.event_callback(pid, _('Command line'),
                                    ' '.join(
                                        readProcessCmdline(event.process.pid)))
                self.event_callback(pid, _('Current working directory'),
                                    readProcessLink(event.process.pid, 'cwd'))
                # If the process has a parent PID include it in the details
                if event.process.parent:
                    self.event_callback(pid, _('Parent PID'),
                                        str(event.process.parent.pid))
                # Add process details
                details = self._get_process_status_details(event.process.pid)
                if UID in details:
                    self.event_callback(pid, _('User ID'), details[UID].pw_uid)
                    self.event_callback(pid, _('User name'),
                                        details[UID].pw_name)
                    self.event_callback(pid, _('User real name'),
                                        details[UID].pw_gecos)
                if EUID in details:
                    self.event_callback(pid, _('Effective user ID'),
                                        details[EUID].pw_uid)
                    self.event_callback(pid, _('Effective user name'),
                                        details[EUID].pw_name)
                    self.event_callback(pid, _('Effective user real name'),
                                        details[EUID].pw_gecos)
                if GID in details:
                    self.event_callback(pid, _('Group ID'),
                                        details[GID].gr_gid)
                    self.event_callback(pid, _('Group name'),
                                        details[GID].gr_name)
                if EGID in details:
                    self.event_callback(pid, _('Effective group ID'),
                                        details[EGID].gr_gid)
                    self.event_callback(pid, _('Effective group name'),
                                        details[EGID].gr_name)
                self.event_callback(pid, information=_('Status'), value=status)

    def _get_process_status_details(self, pid):
        """Get details from process status"""
        dict_result = {}
        status_file = openProc('%s/status' % pid)
        for line in status_file:
            if line.startswith('Uid:'):
                dict_result[UID] = getpwuid(int(line[5:].split('\t')[0]))
                dict_result[EUID] = getpwuid(int(line[5:].split('\t')[1]))
            elif line.startswith('Gid:'):
                dict_result[GID] = getgrgid(int(line[5:].split('\t')[0]))
                dict_result[EGID] = getgrgid(int(line[5:].split('\t')[1]))
        status_file.close()
        return dict_result
