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

from gptrace.constants import APP_NAME, FILE_ICON, FILE_SETTINGS
from gptrace.daemon_thread import DaemonThread
from gptrace.event_tracer import EventTracer
from gptrace.functions import (_,
                               find_button_from_gtktreeviewcolumn,
                               process_events,
                               show_dialog_fileopen)
from gptrace.localize import text_gtk30
from gptrace.models.activities import ModelActivities
from gptrace.models.counts import ModelCounts
from gptrace.models.files import ModelFiles
from gptrace.models.intercepted_syscalls import ModelInterceptedSyscalls
from gptrace.models.processes import ModelProcesses
from gptrace.settings import (Settings,
                              SECTION_APPLICATION,
                              SECTION_ACTIVITIES,
                              SECTION_COUNTS,
                              SECTION_FILES,
                              SECTION_PROCESSES)
from gptrace.syscall_tracer import SyscallTracer
from gptrace.ui.about import UIAbout
from gptrace.ui.base import UIBase
from gptrace.ui.column_headers_visibility import ColumnHeadersVisibility
from gptrace.ui.shortcuts import UIShortcuts

SECTION_WINDOW_NAME = 'main window'


class UIMain(UIBase):
    def __init__(self, application, options):
        super().__init__(filename='main.ui')
        self.application = application
        # Load settings
        self.settings = Settings(FILE_SETTINGS, True)
        self.options = options
        self.load_ui()
        # Prepares the models
        self.model_activities = ModelActivities(self.ui.model_activities)
        self.model_intercepted_syscalls = ModelInterceptedSyscalls(
            self.ui.model_intercepted_syscalls)
        self.model_counts = ModelCounts(self.ui.model_counts)
        self.model_files = ModelFiles(self.ui.model_files)
        self.model_processes = ModelProcesses(self.ui.model_processes)
        # Restore the intercepted syscalls list from settings
        saved_syscalls = self.settings.get_intercepted_syscalls()
        # Restore the options from settings
        self.ui.action_auto_clear_results.set_active(
            self.settings.get_boolean(
                section=SECTION_APPLICATION,
                option='autoclear',
                default=self.ui.action_auto_clear_results.get_active()))
        # Update the Show only called syscalls in counts status
        self.ui.action_counts_only_called.set_active(
            self.settings.get_boolean(
                section=SECTION_COUNTS,
                option='only called',
                default=self.ui.action_counts_only_called.get_active()))
        self.ui.action_counts_only_called.toggled()
        # Update the Show only existing files status
        self.ui.action_files_only_existing.set_active(
            self.settings.get_boolean(
                section=SECTION_FILES,
                option='only existing',
                default=self.ui.action_files_only_existing.get_active()))
        self.ui.action_files_only_existing.toggled()
        self.ui.infobar_information.set_visible(False)
        # Load all the available syscall names
        for syscall in sorted(SYSCALL_NAMES.values()):
            prototype = SYSCALL_PROTOTYPES.get(syscall, ('', ()))
            self.model_intercepted_syscalls.add(items=(
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
            self.model_counts.add(items=(syscall, 0, False))
        self.do_update_intercepted_syscalls_count()
        # Restore visible columns
        for current_section in self.column_headers.get_sections():
            self.column_headers.load_visible_columns(current_section)
        # Set ModelFilter
        self.filtered_items = []
        self.ui.filter_activities.set_visible_func(
            self.check_for_filtered_syscall,
            self.filtered_items)
        # Set counts filter
        self.ui.filter_counts.set_visible_column(
            self.model_counts.COL_VISIBILITY)
        self.ui.filter_counts.refilter()
        # Set counts filter
        self.ui.filter_files.set_visible_column(self.model_files.COL_EXISTING)
        self.ui.filter_files.refilter()
        self.thread_loader = None
        self.debugger = None

    def run(self):
        """Show the UI"""
        self.ui.window.show_all()
        # Set Start/Stop button width as the larger between the two
        # to avoid being resized during the change
        max_width = max(self.ui.button_start.get_allocated_width(),
                        self.ui.button_stop.get_allocated_width())
        self.ui.button_start.set_property('width-request', max_width)
        self.ui.button_stop.set_property('width-request', max_width)
        self.ui.button_stop.set_visible(False)

    def load_ui(self):
        """Load the interface UI"""
        # Initialize translations
        self.ui.action_start.set_label(text_gtk30('_Start'))
        self.ui.action_stop.set_label(text_gtk30('_Stop'))
        self.ui.action_about.set_label(text_gtk30('About'))
        self.ui.action_shortcuts.set_label(text_gtk30('Shortcuts'))
        # Initialize titles and tooltips
        self.set_titles()
        # Initialize Gtk.HeaderBar
        self.ui.header_bar.props.title = self.ui.window.get_title()
        self.ui.window.set_titlebar(self.ui.header_bar)
        self.set_buttons_icons(buttons=[self.ui.button_start,
                                        self.ui.button_stop,
                                        self.ui.button_about,
                                        self.ui.button_options])
        # Set buttons with always show image
        for button in (self.ui.button_start, self.ui.button_stop):
            button.set_always_show_image(True)
        # Set start button as suggested
        self.set_buttons_style_suggested_action(
            buttons=[self.ui.button_start])
        # Set stop button as destructive
        self.set_buttons_style_destructive_action(
            buttons=[self.ui.button_stop])
        self.ui.button_stop.set_visible(False)
        # Associate each TreeViewColumn to the MenuItem used to show/hide
        self.column_headers = ColumnHeadersVisibility(ui=self.ui,
                                                      settings=self.settings)
        for menu, section, items in (
                ('menu_columns_activities', SECTION_ACTIVITIES, (
                        ('column_activities_timestamp',
                         'menuitem_columns_activities_timestamp'),
                        ('column_activities_time',
                         'menuitem_columns_activities_time'),
                        ('column_activities_syscall',
                         'menuitem_columns_activities_syscall'),
                        ('column_activities_format',
                         'menuitem_columns_activities_format'),
                        ('column_activities_pid',
                         'menuitem_columns_activities_pid'),
                        ('column_activities_ip',
                         'menuitem_columns_activities_ip')
                )),
                ('menu_columns_counts', SECTION_COUNTS, (
                        ('column_counts_syscall',
                         'menuitem_columns_counts_syscall'),
                        ('column_counts_count',
                         'menuitem_columns_counts_count'),
                )),
                ('menu_columns_files', SECTION_FILES, (
                        ('column_files_pid',
                         'menuitem_columns_files_pid'),
                        ('column_files_existing',
                         'menuitem_columns_files_existing'),
                        ('column_files_path',
                         'menuitem_columns_files_path'),
                )),
                ('menu_columns_processes', SECTION_PROCESSES, (
                        ('column_processes_pid',
                         'menuitem_columns_processes_pid'),
                        ('column_processes_timestamp',
                         'menuitem_columns_processes_timestamp'),
                        ('column_processes_time',
                         'menuitem_columns_processes_time'),
                        ('column_processes_information',
                         'menuitem_columns_processes_information'),
                )),
        ):
            for column, menuitem in items:
                self.column_headers.add_columns_to_section(section=section,
                                                           column=column,
                                                           menu=menu,
                                                           menuitem=menuitem)
        # Set cellrenderers alignment
        self.ui.cell_activities_timestamp.set_property('xalign', 1.0)
        self.ui.cell_activities_time.set_property('xalign', 1.0)
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
                                   self.on_treeview_button_release_event,
                                   menu)
        # Set various properties
        self.ui.window.set_title(APP_NAME)
        self.ui.window.set_icon_from_file(str(FILE_ICON))
        self.ui.window.set_application(self.application)
        self.label_syscalls_text = self.ui.label_syscalls.get_text()
        # Restore the saved size and position
        self.settings.restore_window_position(window=self.ui.window,
                                              section=SECTION_WINDOW_NAME)
        # Connect signals from the UI file to the functions with the same name
        self.ui.connect_signals(self)

    def on_action_about_activate(self, widget):
        """Show the about dialog"""
        about = UIAbout(parent=self.ui.window,
                        settings=self.settings,
                        options=self.options)
        about.show()
        about.destroy()

    def on_action_shortcuts_activate(self, action):
        """Show the shortcuts dialog"""
        dialog = UIShortcuts(self.ui.window)
        dialog.show()

    def on_action_quit_activate(self, action):
        """Quit the application"""
        # Save settings for window size, intercepted syscalls and visible
        # columns
        self.settings.save_window_position(self.ui.window, SECTION_WINDOW_NAME)
        self.settings.set_intercepted_syscalls(self.model_intercepted_syscalls)
        for section in self.column_headers.get_sections():
            self.column_headers.save_visible_columns(section)
        self.settings.set_boolean(
            section=SECTION_APPLICATION,
            option='autoclear',
            value=self.ui.action_auto_clear_results.get_active())
        self.settings.set_boolean(
            section=SECTION_COUNTS,
            option='only called',
            value=self.ui.action_counts_only_called.get_active())
        self.settings.set_boolean(
            section=SECTION_FILES,
            option='only existing',
            value=self.ui.action_files_only_existing.get_active())
        self.settings.save()
        # Immediately hide the main window and let the events process to handle
        # an instantly close instead of slowly let GTK to empty the model
        # before the window is effectively destroyed
        self.ui.window.hide()
        process_events()
        # Cancel the running thread
        if self.thread_loader and self.thread_loader.is_alive():
            self.thread_loader.cancel()
            self.thread_loader.join()
        self.ui.window.destroy()
        self.application.quit()

    def on_action_options_menu_activate(self, widget):
        """Open the options menu"""
        self.ui.button_options.clicked()

    def on_action_clear_results_activate(self, widget):
        """Clear the results list"""
        self.model_activities.clear()
        self.model_counts.clear_values()
        self.model_files.clear()
        self.model_processes.clear()

    def on_action_counts_only_called_toggled(self, action):
        """Set visibility of syscalls in counts section"""
        if self.ui.action_counts_only_called.get_active():
            self.ui.treeview_counts.set_model(self.ui.filter_counts)
        else:
            self.ui.treeview_counts.set_model(self.ui.model_counts)

    def on_action_files_only_existing_toggled(self, action):
        """Set visibility of only existing files in files section"""
        state = self.ui.action_files_only_existing.get_active()
        # Configure column sort order ID for each column in order to allow
        # the sort if the show only existing files setting is set
        self.ui.column_files_existing.set_sort_column_id(
            state and -1 or self.model_files.COL_EXISTING)
        self.ui.column_files_pid.set_sort_column_id(
            state and -1 or self.model_files.COL_PID)
        self.ui.column_files_path.set_sort_column_id(
            state and -1 or self.model_files.COL_FILEPATH)
        # BUG: GTK+ seems to not react if the sort column ID is changed
        # Set the clickable property again after setting the sort column ID
        self.ui.column_files_existing.set_clickable(True)
        self.ui.column_files_pid.set_clickable(True)
        self.ui.column_files_path.set_clickable(True)
        if state:
            self.ui.treeview_files.set_model(self.ui.filter_files)
            self.ui.label_infobar_content.set_markup(
                _('When <i><b>Show only existing files</b></i> is selected '
                  'the sorting by click on the column headers is disabled'))
        else:
            self.ui.treeview_files.set_model(self.ui.model_files)
        self.ui.infobar_information.set_visible(state)

    def on_action_filter_hide_syscall_activate(self, action):
        """Hide the selected syscall from the results"""
        selection = self.ui.treeview_activities.get_selection()
        if selection:
            model, iter = selection.get_selected()
            if iter:
                # Add the selected syscall to the filtered syscalls list
                iter = self.ui.filter_activities.convert_iter_to_child_iter(
                    iter)
                self.filtered_items.append(self.model_activities.get_syscall(
                    treepath=iter))
                # Filter the results
                self.ui.filter_activities.refilter()

    def on_action_filter_show_only_syscall_activate(self, action):
        """Show only the selected syscall from the results"""
        selection = self.ui.treeview_activities.get_selection()
        if selection:
            model, iter = selection.get_selected()
            if iter:
                while len(self.filtered_items):
                    self.filtered_items.pop()
                # First include every syscall names to the filtered syscalls
                self.filtered_items.extend(SYSCALL_NAMES.values())
                # Then remove the selected syscall from the filtered syscalls
                # list
                iter = self.ui.filter_activities.convert_iter_to_child_iter(
                    iter)
                self.filtered_items.remove(self.model_activities.get_syscall(
                    treepath=iter))
                # Filter the results
                self.ui.filter_activities.refilter()

    def on_action_filter_reset_syscalls_activate(self, action):
        """Clear the filtered syscalls list including all"""
        while len(self.filtered_items):
            self.filtered_items.pop()
        self.ui.filter_activities.refilter()

    def on_action_start_activate(self, action):
        """Start debugger"""
        if self.ui.action_auto_clear_results.get_active():
            self.ui.action_clear_results.activate()
        # Disable file chooser and set stop icon
        self.ui.text_program.set_sensitive(False)
        self.ui.action_start.set_sensitive(False)
        self.ui.action_stop.set_sensitive(True)
        self.ui.action_browse.set_sensitive(False)
        self.ui.text_program.set_property('secondary-icon-sensitive', False)
        self.ui.button_start.set_visible(False)
        self.ui.button_stop.set_visible(True)
        # Start debugger
        self.thread_loader = DaemonThread(
            target=self.do_debug_process,
            args=(shlex.split(self.ui.text_program.get_text()),)
        )
        self.thread_loader.start()

    def on_action_stop_activate(self, action):
        """Stop the running debugger"""
        if self.thread_loader:
            self.thread_loader.cancel()
            try:
                # Race condition, the debugger may be set to None
                self.debugger.quit()
            except AttributeError:
                pass
            # Restore file chooser and set execute icon
            self.ui.text_program.set_sensitive(True)
            self.ui.action_start.set_sensitive(True)
            self.ui.action_stop.set_sensitive(False)
            self.ui.action_browse.set_sensitive(True)
            self.ui.text_program.set_property('secondary-icon-sensitive', True)
            self.ui.button_start.set_visible(True)
            self.ui.button_stop.set_visible(False)

    def on_action_browse_activate(self, action):
        """Select the program to open"""
        if program := show_dialog_fileopen(
                parent=self.ui.window,
                title=_("Select a program to execute")):
            self.ui.text_program.set_text(program)

    def on_action_syscalls_select_all_activate(self, action):
        """Intercept all the syscalls"""
        for row in self.model_intercepted_syscalls:
            self.model_intercepted_syscalls.set_checked(row, True)
        self.do_update_intercepted_syscalls_count()

    def on_action_syscalls_file_activate(self, action):
        """Intercept all the syscalls that use filenames"""
        for row in self.model_intercepted_syscalls:
            if self.model_intercepted_syscalls.get_has_filename_arguments(row):
                self.model_intercepted_syscalls.set_checked(row, True)
        self.do_update_intercepted_syscalls_count()

    def on_action_syscalls_socket_activate(self, action):
        """Intercept all the syscalls used by sockets"""
        for row in self.model_intercepted_syscalls:
            if self.model_intercepted_syscalls.get_socket_function(row):
                self.model_intercepted_syscalls.set_checked(row, True)
        self.do_update_intercepted_syscalls_count()

    def on_action_syscalls_clear_activate(self, action):
        """Disable any syscall to intercept"""
        for row in self.model_intercepted_syscalls:
            self.model_intercepted_syscalls.set_checked(row, False)
        self.do_update_intercepted_syscalls_count()

    def on_cell_syscalls_checked_toggled(self, widget, treepath):
        """Handle click on the checked column"""
        self.model_intercepted_syscalls.toggle_checked(treepath)
        self.do_update_intercepted_syscalls_count()

    def on_infobar_information_response(self, widget, response):
        """Click on the infobar buttons"""
        if response == Gtk.ResponseType.CLOSE:
            self.ui.infobar_information.set_visible(False)

    def on_text_program_changed(self, widget):
        """Enable or disable the action if a program path was set"""
        self.ui.action_start.set_sensitive(
            len(self.ui.text_program.get_text()) > 0)

    def on_text_program_icon_release(self, widget, icon_position, event):
        """Click an icon next to a Entry"""
        if icon_position == Gtk.EntryIconPosition.SECONDARY:
            self.ui.action_browse.activate()

    def on_treeview_button_release_event(self, widget, event, menu):
        """Show columns visibility menu on right click"""
        if event.button == Gdk.BUTTON_SECONDARY:
            self.show_popup_menu(menu)

    def on_window_delete_event(self, widget, event):
        """Close the application by closing the main window"""
        self.ui.action_quit.activate()

    def do_debug_process(self, program):
        """Debug the requested program to trace the syscalls"""

        def add_process(pid, information, value):
            """Add a process information"""
            now = datetime.datetime.now()
            GObject.idle_add(self.model_processes.add, (
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
            ignore_syscall_callback=self.do_syscall_callback_ignore,
            syscall_callback=self.do_syscall_callback,
            event_callback=EventTracer(add_process).handle_event,
            quit_callback=self.do_quit_callback)
        self.debugger.main()
        return True

    def do_syscall_callback(self, syscall):
        """Add the syscall to the syscalls model"""
        now = datetime.datetime.now()
        GObject.idle_add(self.model_activities.add, (
            (now - self.debug_start_time).total_seconds(),
            now.strftime('%H:%M:%S.%f'),
            syscall.name,
            syscall.format(),
            syscall.process.pid,
            formatAddress(syscall.instr_pointer)
        ))
        GObject.idle_add(self.model_counts.increment_count, syscall.name)
        # Check if the syscall has any filename or pathname argument
        for argument in syscall.arguments:
            argument_text = argument.getText()
            if (argument.name in FILENAME_ARGUMENTS and
                    argument_text != "''..."):
                GObject.idle_add(self.model_files.add, (
                    str(syscall.process.pid),
                    argument_text[1:-1],
                    os.path.exists(argument_text[1:-1])))

    def do_syscall_callback_ignore(self, syscall):
        """Determine if to ignore a callback before it's processed"""
        if syscall.name in self.model_intercepted_syscalls.syscalls:
            # Process the syscall
            return False
        else:
            # Ignore the syscall
            return True

    def do_quit_callback(self):
        """The debugger is quitting"""
        self.ui.action_stop.activate()

    def do_update_intercepted_syscalls_count(self):
        """Update the intercepted syscalls count label"""
        self.ui.label_syscalls.set_text(
            self.label_syscalls_text % {
                'selected': len(self.model_intercepted_syscalls.syscalls),
                'total': self.model_intercepted_syscalls.count(),
            })

    def on_menuitemVisibleColumns_toggled(self, widget):
        """Hide or show a column header"""
        for section in self.column_headers.get_sections():
            for (column, menu, menuitem) in self.column_headers.get_values(
                    section):
                # Set column visibility
                if widget is menuitem:
                    column.set_visible(widget.get_active())
                    break

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
        selection = self.ui.treeview_activities.get_selection()
        if selection:
            model, iter = selection.get_selected()
            if iter:
                # Get the syscall name to ignore/unignore
                selected_syscall = self.model_activities.get_syscall(
                    self.ui.filter_activities.convert_iter_to_child_iter(iter))
                # Cycle each row in the intercepted syscalls model
                for row in self.model_intercepted_syscalls:
                    # If the syscall name for the row is the same then
                    # ignore/unignore
                    if self.model_intercepted_syscalls.get_syscall(
                            row) == selected_syscall:
                        self.model_intercepted_syscalls.set_checked(
                            treepath=row,
                            value=status)
                        break
                # Update the intercepted syscalls count
                self.do_update_intercepted_syscalls_count()

    def on_treeview_activities_button_release_event(self, widget, event):
        """Show filter menu on right click"""
        if event.button == Gdk.BUTTON_SECONDARY:
            if self.ui.treeview_activities.get_path_at_pos(int(event.x),
                                                           int(event.y)):
                self.show_popup_menu(self.ui.menuActivitiesFilter)

    def check_for_filtered_syscall(self, model, iter, data):
        """Check if the sycall name should be filtered"""
        return (self.model_activities.get_syscall(iter) not in
                self.filtered_items)
