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

import logging

from ptrace import PtraceError
from ptrace.debugger import (PtraceDebugger,
                             Application,
                             ProcessExit,
                             ProcessSignal,
                             NewProcessEvent,
                             ProcessExecution,
                             ChildError)
from ptrace.func_call import FunctionCallOptions


class SyscallTracer(Application):
    def __init__(self, options, program, ignore_syscall_callback,
                 syscall_callback, event_callback, quit_callback):
        logging.info(f'Starting debug for: {program}')
        Application.__init__(self)
        # Parse self.options
        self.options = options
        self.program = program
        self.debugger = None
        self.syscall_options = None
        self.processOptions()
        self.ignore_syscall_callback = ignore_syscall_callback
        self.syscall_callback = syscall_callback
        self.event_callback = event_callback
        self.quit_callback = quit_callback

    def run_debugger(self):
        """Create debugger and traced process"""
        logging.info('Started debugger')
        self.setupDebugger()
        process = self.createProcess()
        if not process:
            return

        self.syscall_options = FunctionCallOptions(
            write_types=True,
            write_argname=True,
            replace_socketcall=False,
            string_max_length=300,
            write_address=False,
            max_array_count=20,
        )
        self.syscall_options.instr_pointer = self.options.show_ip
        self.syscall_trace(process)

    def display_syscall(self, syscall):
        self.syscall_callback(syscall)

    def syscall(self, process):
        state = process.syscall_state
        syscall = state.event(self.syscall_options)
        if syscall and (syscall.result is not None or self.options.enter):
            self.display_syscall(syscall)
        # Break at next syscall
        process.syscall()

    def syscall_trace(self, process):
        # First query to break at next syscall
        self.process_prepare(process)

        while True:
            # No more process? Exit
            if not self.debugger:
                logging.debug('The debugger has exited')
                break
            # Wait until next syscall enter
            try:
                event = self.debugger.waitSyscall()
                process = event.process
            except ProcessExit as event:
                logging.debug('A process has exited')
                self.process_exited(event)
                continue
            except ProcessSignal as event:
                self.event_callback(event)
                # event.display()
                process.syscall(event.signum)
                continue
            except NewProcessEvent as event:
                logging.debug('A new process is spawned')
                self.event_callback(event)
                process = event.process
                self.process_prepare(process)
                process.parent.syscall()
                continue
            except ProcessExecution as event:
                self.event_callback(event)
                process = event.process
                process.syscall()
                continue
            except IndexError as error:
                logging.error(f'IndexError: {error}')
                continue

            # Process syscall enter or exit
            self.syscall(process)

    def process_prepare(self, process):
        process.syscall()
        process.syscall_state.ignore_callback = self.ignore_syscall_callback

    def process_exited(self, event):
        # Display syscall which has not exited
        state = event.process.syscall_state
        if (state.next_event == "exit") and (
                not self.options.enter) and state.syscall:
            self.display_syscall(state.syscall)
        self.event_callback(event)

    def main(self):
        self.debugger = PtraceDebugger()
        try:
            self.run_debugger()
        except ChildError as event:
            self.event_callback(event)
        except ProcessExit as event:
            self.process_exited(event)
        except (KeyError, PtraceError, OSError) as error:
            self._handle_exceptions_during_quit(error, 'main')
        if self.debugger:
            self.debugger.quit()
        self.quit_callback()

    def quit(self):
        try:
            self.debugger.quit()
        except (KeyError, PtraceError, OSError) as error:
            self._handle_exceptions_during_quit(error, 'quit')
        self.quit_callback()
        self.debugger = None

    def _handle_exceptions_during_quit(self, exception, context):
        if isinstance(exception, KeyError):
            # When the debugger is waiting for a syscall and the debugger
            # process is closed with quit() a KeyError Exception for missing
            # PID is fired
            pass
        elif isinstance(exception, PtraceError):
            logging.error(f'PtraceError from {context}: {exception}')
        elif isinstance(exception, OSError):
            logging.error(f'OSError from {context}: {exception}')
        else:
            logging.error(f'Unexpected exception from {context}')
