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

import datetime
import optparse
import os.path
import shlex

from gi.repository import GObject
from gi.repository import Gdk
from gi.repository import Gtk
from ptrace.ctypes_tools import formatAddress
from ptrace.syscall import (SYSCALL_NAMES,
                            SYSCALL_PROTOTYPES,
                            FILENAME_ARGUMENTS,
                            SOCKET_SYSCALL_NAMES)

from gptrace.constants import APP_NAME, FILE_ICON
from gptrace.daemon_thread import DaemonThread
from gptrace.event_tracer import EventTracer
from gptrace.functions import (_,
                               get_ui_file,
                               find_button_from_gtktreeviewcolumn,
                               process_events,
                               show_dialog_fileopen,
                               show_popup_menu)
from gptrace.gtkbuilder_loader import GtkBuilderLoader
from gptrace.models.activities import ModelActivities
from gptrace.models.counts import ModelCounts
from gptrace.models.files import ModelFiles
from gptrace.models.intercepted_syscalls import ModelInterceptedSyscalls
from gptrace.models.processes import ModelProcesses
from gptrace.settings import (SECTION_APPLICATION,
                              SECTION_ACTIVITIES,
                              SECTION_COUNTS,
                              SECTION_FILES,
                              SECTION_PROCESSES)
from gptrace.syscall_tracer import SyscallTracer
from .about import AboutWindow
from .main_column_headers import ShowHideColumnHeaders


class MainWindow(object):
    def __init__(self, application, settings):
        self.application = application
        self.ui = GtkBuilderLoader(get_ui_file('main.glade'))
        self.settings = settings
        self.load_ui()
        # Restore the intercepted syscalls list from settings
        saved_syscalls = settings.get_intercepted_syscalls()
        # Restore the options from settings
        self.ui.menuitemAutoClear.set_active(self.settings.get_boolean(
            section=SECTION_APPLICATION,
            name='autoclear',
            default=self.ui.menuitemAutoClear.get_active()))
        # Update the Show only called syscalls in counts status
        self.ui.menuitemCountsOnlyCalled.set_active(self.settings.get_boolean(
            section=SECTION_COUNTS,
            name='only called',
            default=self.ui.menuitemCountsOnlyCalled.get_active()))
        self.on_menuitemCountsOnlyCalled_toggled(None)
        # Update the Show only existing files status
        self.ui.menuitemFilesShowOnlyExisting.set_active(
            self.settings.get_boolean(
                section=SECTION_FILES,
                name='only existing',
                default=self.ui.menuitemFilesShowOnlyExisting.get_active()))
        self.on_menuitemFilesShowOnlyExisting_toggled(None)
        self.ui.infobarInformation.set_visible(False)
        # Load all the available syscall names
        for syscall in sorted(SYSCALL_NAMES.values()):
            prototype = SYSCALL_PROTOTYPES.get(syscall, ('', ()))
            self.modelInterceptedSyscalls.add(items=(
                # If the configuration file has a list of intercepted syscalls
                # then set each syscall status accordingly
                saved_syscalls is None and True or syscall in saved_syscalls,
                # Add syscall name
                syscall,
                # Add return type
                prototype[0],
                # Add prototype arguments
                ', '.join(['%s %s' % m for m in prototype[1]]),
                # Does this syscall use any filename/pathname argument?
                any(argname in FILENAME_ARGUMENTS for argtype, argname in
                    prototype[1]),
                # Is this syscall used by sockets?
                syscall in SOCKET_SYSCALL_NAMES,
            ))
            self.modelCounts.add(items=(syscall, 0, False))
        self.update_InterceptedSyscalls_count()
        # Restore the saved size and position
        if self.settings.get_value('width', 0) and self.settings.get_value(
                'height', 0):
            self.ui.winMain.set_default_size(
                self.settings.get_value('width', -1),
                self.settings.get_value('height', -1))
        if (self.settings.get_value('left', 0) and
                self.settings.get_value('top', 0)):
            self.ui.winMain.move(
                self.settings.get_value('left', 0),
                self.settings.get_value('top', 0))
        # Restore visible columns
        for current_section in self.column_headers.get_sections():
            self.column_headers.load_visible_columns(current_section)
        # Set ModelFilter
        self.filtered_items = []
        self.ui.filterActivities.set_visible_func(
            self.check_for_filtered_syscall,
            self.filtered_items)
        # Set counts filter
        self.ui.filterCounts.set_visible_column(
            self.modelCounts.COL_VISIBILITY)
        self.ui.filterCounts.refilter()
        # Set counts filter
        self.ui.filterFiles.set_visible_column(self.modelFiles.COL_EXISTING)
        self.ui.filterFiles.refilter()
        # Load the others dialogs
        self.about = AboutWindow(self.ui.winMain, False)
        self.thread_loader = None
        self.debugger = None

    def run(self):
        """Show the UI"""
        self.ui.winMain.show_all()

    def load_ui(self):
        """Load the interface UI"""
        self.modelActivities = ModelActivities(self.ui.storeActivities)
        self.modelInterceptedSyscalls = ModelInterceptedSyscalls(
            self.ui.storeInterceptedSyscalls)
        self.modelCounts = ModelCounts(self.ui.storeCounts)
        self.modelFiles = ModelFiles(self.ui.storeFiles)
        self.modelProcesses = ModelProcesses(self.ui.storeProcesses)

        # Associate each TreeViewColumn to the MenuItem used to show/hide
        self.column_headers = ShowHideColumnHeaders(self.ui.get_object,
                                                    self.settings)
        for menu, section, items in (
                ('menuActivitiesVisibleColumns', SECTION_ACTIVITIES, (
                        ('colActivitiesTimestamp',
                         'menuitemActivitiesVisibleColumnsTimestamp'),
                        ('colActivitiesTime',
                         'menuitemActivitiesVisibleColumnsTime'),
                        ('colActivitiesSyscall',
                         'menuitemActivitiesVisibleColumnsSyscall'),
                        ('colActivitiesFormat',
                         'menuitemActivitiesVisibleColumnsFormat'),
                        ('colActivitiesPID',
                         'menuitemActivitiesVisibleColumnsPID'),
                        ('colActivitiesIP',
                         'menuitemActivitiesVisibleColumnsIP')
                )),
                ('menuCountsVisibleColumns', SECTION_COUNTS, (
                        ('colCountsSyscall',
                         'menuitemCountsVisibleColumnsSyscall'),
                        ('colCountsCount',
                         'menuitemCountsVisibleColumnsCount'),
                )),
                ('menuFilesVisibleColumns', SECTION_FILES, (
                        ('colFilesPID', 'menuitemFilesVisibleColumnsPID'),
                        ('colFilesExisting',
                         'menuitemFilesVisibleColumnsExisting'),
                        ('colFilesPath', 'menuitemFilesVisibleColumnsPath'),
                )),
                ('menuProcessesVisibleColumns', SECTION_PROCESSES, (
                        ('colProcessesPID',
                         'menuitemProcessesVisibleColumnsPID'),
                        ('colProcessesTimestamp',
                         'menuitemProcessesVisibleColumnsTimestamp'),
                        ('colProcessesTime',
                         'menuitemProcessesVisibleColumnsTime'),
                        ('colProcessesInformation',
                         'menuitemProcessesVisibleColumnsInformation'),
                )),
        ):
            for column, menuitem in items:
                self.column_headers.add_columns_to_section(section, column,
                                                           menu, menuitem)
        # Set cellrenderers alignment
        self.ui.cellActivitiesTimestamp.set_property('xalign', 1.0)
        self.ui.cellActivitiesTime.set_property('xalign', 1.0)
        # Set options menu items value as their column headers
        for section in self.column_headers.get_sections():
            for (column, menu, menuitem) in self.column_headers.get_values(
                    section):
                # Set the MenuItem label as the TreeViewColumn header
                menuitem.set_label(column.get_title())
                # Set button-press-event to the Button contained inside the
                # TreeViewColumn
                button = find_button_from_gtktreeviewcolumn(column)
                if button:
                    # Set a signal callback to the Button
                    button.connect('button-press-event',
                                   self.on_tvwcolumn_button_release_event,
                                   menu)
        # Set various properties
        self.ui.winMain.set_title(APP_NAME)
        self.ui.winMain.set_icon_from_file(FILE_ICON)
        self.ui.winMain.set_application(self.application)
        self.lblInterceptedSyscalls_descr = (
            self.ui.lblInterceptedSyscalls.get_text())
        # Connect signals from the glade file to the functions with the
        # same name
        self.ui.connect_signals(self)

    def on_winMain_delete_event(self, widget, event):
        """Close the application"""
        # Save settings for window size, intercepted syscalls and visible
        # columns
        self.settings.set_sizes(self.ui.winMain)
        self.settings.set_intercepted_syscalls(self.modelInterceptedSyscalls)
        for section in self.column_headers.get_sections():
            self.column_headers.save_visible_columns(section)
        self.settings.set_boolean(
            section=SECTION_APPLICATION,
            name='autoclear',
            value=self.ui.menuitemAutoClear.get_active())
        self.settings.set_boolean(
            section=SECTION_COUNTS,
            name='only called',
            value=self.ui.menuitemCountsOnlyCalled.get_active())
        self.settings.set_boolean(
            section=SECTION_FILES,
            name='only existing',
            value=self.ui.menuitemFilesShowOnlyExisting.get_active())
        self.settings.save()
        # Immediately hide the main window and let the events process to handle
        # an instantly close instead of slowly let GTK to empty the model
        # before the window is effectively destroyed
        self.ui.winMain.hide()
        process_events()
        # Cancel the running thread
        if self.thread_loader and self.thread_loader.is_alive():
            self.thread_loader.cancel()
            self.thread_loader.join()
        self.about.destroy()
        self.ui.winMain.destroy()
        self.application.quit()

    def on_btnAbout_clicked(self, widget):
        """Show the about dialog"""
        self.about.show()

    def on_txtProgram_icon_release(self, widget, icon_position, event):
        """Click an icon next to a Entry"""
        if icon_position == Gtk.EntryIconPosition.SECONDARY:
            self.ui.txtProgram.set_text('')

    def on_txtProgram_changed(self, widget):
        """Enable or disable the button if a program path was set"""
        self.ui.btnStartStop.set_sensitive(
            len(self.ui.txtProgram.get_text()) > 0)

    def thread_debug_process(self, program):
        """Debug the requested program to trace the syscalls"""

        def add_process(pid, information, value):
            """Add a process information"""
            now = datetime.datetime.now()
            GObject.idle_add(self.modelProcesses.add, (
                str(pid),
                (now - self.debug_start_time).total_seconds(),
                now.strftime('%H:%M:%S.%f'),
                information,
                str(value).strip()))

        self.debug_start_time = datetime.datetime.now()
        self.debugger = SyscallTracer(
            options=optparse.Values({
                'fork': True,
                'enter': False,
                'show_ip': True,
                'trace_exec': True,
                'trace_clone': True,
                'no_stdout': False,
                'pid': None,
                'show_pid': True,
            }),
            program=program,
            ignore_syscall_callback=self.ignore_syscall_callback,
            syscall_callback=self.syscall_callback,
            event_callback=EventTracer(add_process).handle_event,
            quit_callback=self.quit_callback)
        self.debugger.main()
        return True

    def syscall_callback(self, syscall):
        """Add the syscall to the syscalls model"""
        now = datetime.datetime.now()
        GObject.idle_add(self.modelActivities.add, (
            (now - self.debug_start_time).total_seconds(),
            now.strftime('%H:%M:%S.%f'),
            syscall.name,
            syscall.format(),
            syscall.process.pid,
            formatAddress(syscall.instr_pointer)
        ))
        GObject.idle_add(self.modelCounts.increment_count, syscall.name)
        # Check if the syscall has any filename or pathname argument
        for argument in syscall.arguments:
            argument_text = argument.getText()
            if (argument.name in FILENAME_ARGUMENTS and
                    argument_text != "''..."):
                GObject.idle_add(self.modelFiles.add, (
                    str(syscall.process.pid),
                    argument_text[1:-1],
                    os.path.exists(argument_text[1:-1])))

    def ignore_syscall_callback(self, syscall):
        """Determine if to ignore a callback before it's processed"""
        if syscall.name in self.modelInterceptedSyscalls.syscalls:
            # Process the syscall
            return False
        else:
            # Ignore the syscall
            return True

    def quit_callback(self):
        """The debugger is quitting"""
        self.ui.btnStartStop.set_active(False)

    def on_cellInterceptedChecked_toggled(self, widget, treepath):
        """Handle click on the checked column"""
        self.modelInterceptedSyscalls.toggle_checked(treepath)
        self.update_InterceptedSyscalls_count()

    def on_btnInterceptedSyscallsSelectAll_clicked(self, widget):
        """Intercept all the syscalls"""
        for row in self.modelInterceptedSyscalls:
            self.modelInterceptedSyscalls.set_checked(row, True)
        self.update_InterceptedSyscalls_count()

    def on_btnInterceptedSyscallsClear_clicked(self, widget):
        """Disable any syscall to intercept"""
        for row in self.modelInterceptedSyscalls:
            self.modelInterceptedSyscalls.set_checked(row, False)
        self.update_InterceptedSyscalls_count()

    def on_btnInterceptedSyscallsSelectForFile_clicked(self, widget):
        """Intercept all the syscalls that use filenames"""
        for row in self.modelInterceptedSyscalls:
            if self.modelInterceptedSyscalls.get_has_filename_arguments(row):
                self.modelInterceptedSyscalls.set_checked(row, True)
        self.update_InterceptedSyscalls_count()

    def on_btnInterceptedSyscallsSelectForSocket_clicked(self, widget):
        """Intercept all the syscalls used by sockets"""
        for row in self.modelInterceptedSyscalls:
            if self.modelInterceptedSyscalls.get_socket_function(row):
                self.modelInterceptedSyscalls.set_checked(row, True)
        self.update_InterceptedSyscalls_count()

    def update_InterceptedSyscalls_count(self):
        """Update the intercepted syscalls count label"""
        self.ui.lblInterceptedSyscalls.set_text(
            self.lblInterceptedSyscalls_descr % {
                'selected': len(self.modelInterceptedSyscalls.syscalls),
                'total': self.modelInterceptedSyscalls.count(),
            })

    def on_btnOptions_clicked(self, widget):
        """Show the options popup menu"""
        show_popup_menu(self.ui.menuOptions)

    def on_menuitemVisibleColumns_toggled(self, widget):
        """Hide or show a column header"""
        for section in self.column_headers.get_sections():
            for (column, menu, menuitem) in self.column_headers.get_values(
                    section):
                # Set column visibility
                if widget is menuitem:
                    column.set_visible(widget.get_active())
                    break

    def on_tvwcolumn_button_release_event(self, widget, event, menu):
        """Show columns visibility menu on right click"""
        if event.button == Gdk.BUTTON_SECONDARY:
            show_popup_menu(menu)

    def on_btnStartStop_toggled(self, widget):
        """Start and stop program tracing"""
        if self.ui.btnStartStop.get_active():
            if self.ui.txtProgram.get_text():
                if self.ui.menuitemAutoClear.get_active():
                    self.on_menuitemClear_activate(None)
                # Disable file chooser and set stop icon
                self.ui.txtProgram.set_sensitive(False)
                self.ui.btnProgramOpen.set_sensitive(False)
                self.ui.btnStartStop.set_image(self.ui.image_stop)
                # Start debugger
                self.thread_loader = DaemonThread(
                    target=self.thread_debug_process,
                    args=(shlex.split(self.ui.txtProgram.get_text()),)
                )
                self.thread_loader.start()
            else:
                # If no filename was selected then set button status as
                # unpressed
                self.ui.btnStartStop.set_active(False)
        else:
            # Cancel running debugger
            if self.thread_loader:
                self.thread_loader.cancel()
                self.debugger.quit()
                # Restore file chooser and set execute icon
                self.ui.txtProgram.set_sensitive(True)
                self.ui.btnProgramOpen.set_sensitive(True)
                self.ui.btnStartStop.set_image(self.ui.image_start)

    def on_menuitemClear_activate(self, widget):
        """Clear the syscalls list"""
        self.modelActivities.clear()
        self.modelCounts.clear_values()
        self.modelFiles.clear()
        self.modelProcesses.clear()

    def on_menuitemActivitiesFilterHideSyscall_activate(self, widget):
        """Hide the selected syscall from the results"""
        selection = self.ui.tvwActivities.get_selection()
        if selection:
            model, iter = selection.get_selected()
            if iter:
                # Add the selected syscall to the filtered syscalls list
                self.filtered_items.append(self.modelActivities.get_syscall(
                    self.ui.filterActivities.convert_iter_to_child_iter(iter)))
                # Filter the results
                self.ui.filterActivities.refilter()

    def on_menuitemActivitiesFilterShowOnlySyscall_activate(self, widget):
        """Show only the selected syscall from the results"""
        selection = self.ui.tvwActivities.get_selection()
        if selection:
            model, iter = selection.get_selected()
            if iter:
                while len(self.filtered_items):
                    self.filtered_items.pop()
                # First include every syscall names to the filtered syscalls
                self.filtered_items.extend(SYSCALL_NAMES.values())
                # Then remove the selected syscall from the filtered syscalls
                # list
                self.filtered_items.remove(self.modelActivities.get_syscall(
                    self.ui.filterActivities.convert_iter_to_child_iter(iter)))
                # Filter the results
                self.ui.filterActivities.refilter()

    def on_menuitemActivitiesIgnoreSyscall_activate(self, widget):
        """
        Remove the selected syscall name from the intercepted syscalls model
        """
        self.on_menuitemActivitiesIgnoreUnignoreSyscall(False)

    def on_menuitemActivitiesUnignoreSyscall_activate(self, widget):
        """Add the selected syscall name to the intercepted syscalls model"""
        self.on_menuitemActivitiesIgnoreUnignoreSyscall(True)

    def on_menuitemActivitiesIgnoreUnignoreSyscall(self, status):
        """
        Add or remove the selected syscall name from the intercepted syscalls
        model
        """
        selection = self.ui.tvwActivities.get_selection()
        if selection:
            model, iter = selection.get_selected()
            if iter:
                # Get the syscall name to ignore/unignore
                selected_syscall = self.modelActivities.get_syscall(
                    self.ui.filterActivities.convert_iter_to_child_iter(iter))
                # Cycle each row in the intercepted syscalls model
                for row in self.modelInterceptedSyscalls:
                    # If the syscall name for the row is the same then
                    # ignore/unignore
                    if self.modelInterceptedSyscalls.get_syscall(
                            row) == selected_syscall:
                        self.modelInterceptedSyscalls.set_checked(row, status)
                        break
                # Update the intercepted syscalls count
                self.update_InterceptedSyscalls_count()

    def on_menuitemActivitiesFilterReset_activate(self, widget):
        """Clear the filtered syscalls list including all"""
        while len(self.filtered_items):
            self.filtered_items.pop()
        self.ui.filterActivities.refilter()

    def on_tvwActivities_button_release_event(self, widget, event):
        """Show filter menu on right click"""
        if event.button == Gdk.BUTTON_SECONDARY:
            current_selection = self.ui.tvwActivities.get_path_at_pos(
                int(event.x), int(event.y))
            if current_selection:
                show_popup_menu(self.ui.menuActivitiesFilter)

    def check_for_filtered_syscall(self, model, iter, data):
        """Check if the sycall name should be filtered"""
        return (self.modelActivities.get_syscall(iter) not in
                self.filtered_items)

    def on_btnProgramOpen_clicked(self, widget):
        """Select the program to open"""
        program = show_dialog_fileopen(
            parent=self.ui.winMain,
            title=_("Select a program to execute"))
        if program:
            self.ui.txtProgram.set_text(program)

    def on_menuitemCountsOnlyCalled_toggled(self, widget):
        """Set visibility of syscalls in counts section"""
        if self.ui.menuitemCountsOnlyCalled.get_active():
            self.ui.tvwCounts.set_model(self.ui.filterCounts)
        else:
            self.ui.tvwCounts.set_model(self.ui.storeCounts)

    def on_menuitemFilesShowOnlyExisting_toggled(self, widget):
        """Set visibility of only existing files in files section"""
        state = self.ui.menuitemFilesShowOnlyExisting.get_active()
        # Configure column sort order ID for each column in order to allow
        # the sort if the show only existing files setting is set
        self.ui.colFilesExisting.set_sort_column_id(
            state and -1 or self.modelFiles.COL_EXISTING)
        self.ui.colFilesPID.set_sort_column_id(
            state and -1 or self.modelFiles.COL_PID)
        self.ui.colFilesPath.set_sort_column_id(
            state and -1 or self.modelFiles.COL_FILEPATH)
        # BUG: GTK+ seems to not react if the sort column ID is changed
        # Set the clickable property again after setting the sort column ID
        self.ui.colFilesExisting.set_clickable(True)
        self.ui.colFilesPID.set_clickable(True)
        self.ui.colFilesPath.set_clickable(True)
        if state:
            self.ui.tvwFiles.set_model(self.ui.filterFiles)
            self.ui.lblInfoBarContent.set_markup(
                _('When <i><b>Show only existing files</b></i> is selected '
                  'the sorting by click on the column headers is disabled'))
        else:
            self.ui.tvwFiles.set_model(self.ui.storeFiles)
        self.ui.infobarInformation.set_visible(state)

    def on_infobar1_response(self, widget, response):
        if response == Gtk.ResponseType.CLOSE:
            self.ui.infobarInformation.set_visible(False)
