##
#     Project: gpTrace
# Description: Trace the activities of an external application
#      Author: Fabio Castelli (Muflone) <webreg@vbsimple.net>
#   Copyright: 2014 Fabio Castelli
#     License: GPL-2+
#  This program is free software; you can redistribute it and/or modify it
#  under the terms of the GNU General Public License as published by the Free
#  Software Foundation; either version 2 of the License, or (at your option)
#  any later version.
#
#  This program is distributed in the hope that it will be useful, but WITHOUT
#  ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
#  FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
#  more details.
#  You should have received a copy of the GNU General Public License along
#  with this program; if not, write to the Free Software Foundation, Inc.,
#  51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA
##

import optparse
import datetime
import shlex
import grp
import pwd

from gi.repository import Gtk
from gi.repository import Gio
from gi.repository import GObject
from gi.repository import Gdk

from .about import AboutWindow

from gptrace.constants import *
from gptrace.functions import *
from gptrace.settings import Settings, SECTION_APPLICATION, SECTION_ACTIVITIES, SECTION_COUNTS, SECTION_FILES
from gptrace.models.activities import ModelActivities
from gptrace.models.intercepted_syscalls import ModelInterceptedSyscalls
from gptrace.models.counts import ModelCounts
from gptrace.models.files import ModelFiles
from gptrace.models.processes import ModelProcesses
from gptrace.gtkbuilder_loader import GtkBuilderLoader
from gptrace.daemon_thread import DaemonThread
from gptrace.syscall_tracer import SyscallTracer

from ptrace.syscall import SYSCALL_NAMES, SYSCALL_PROTOTYPES, FILENAME_ARGUMENTS, SOCKET_SYSCALL_NAMES
from ptrace.ctypes_tools import formatAddress
from ptrace.debugger.process_event import NewProcessEvent, ProcessExecution, ProcessExit
from ptrace.debugger.ptrace_signal import ProcessSignal
from ptrace.debugger.child import ChildError
from ptrace.os_tools import RUNNING_LINUX

if RUNNING_LINUX:
  from ptrace.linux_proc import readProcessCmdline, readProcessLink, openProc

class MainWindow(object):
  def __init__(self, application, settings):
    self.application = application
    self.ui = GtkBuilderLoader(FILE_UI_MAIN)
    self.loadUI()
    self.settings = settings
    # Restore the intercepted syscalls list from settings
    saved_syscalls = settings.get_intercepted_syscalls()
    # Restore the options from settings
    self.ui.menuitemAutoClear.set_active(self.settings.get_boolean(
      SECTION_APPLICATION, 'autoclear',
      self.ui.menuitemAutoClear.get_active()))
    # Update the Show only called syscalls in counts status
    self.ui.menuitemCountsOnlyCalled.set_active(self.settings.get_boolean(
      SECTION_COUNTS, 'only called',
      self.ui.menuitemCountsOnlyCalled.get_active()))
    self.on_menuitemCountsOnlyCalled_toggled(None)
    # Update the Show only existing files status
    self.ui.menuitemFilesShowOnlyExisting.set_active(self.settings.get_boolean(
      SECTION_FILES, 'only existing',
      self.ui.menuitemFilesShowOnlyExisting.get_active()))
    self.on_menuitemFilesShowOnlyExisting_toggled(None)
    self.ui.infobarInformation.set_visible(False)
    # Load all the available syscall names
    for syscall in sorted(SYSCALL_NAMES.values()):
      prototype = SYSCALL_PROTOTYPES.get(syscall, ('', ( )))
      self.modelInterceptedSyscalls.add(items=(
        # If the configuration file has a list of intercepted syscalls then
        # set each syscall status accordingly
        saved_syscalls is None and True or syscall in saved_syscalls,
        # Add syscall name
        syscall,
        # Add return type
        prototype[0],
        # Add prototype arguments
        ', '.join(['%s %s' % m for m in prototype[1]]),
        # Does this syscall use any filename/pathname argument?
        any(argname in FILENAME_ARGUMENTS for argtype, argname in prototype[1]),
        # Is this syscall used by sockets?
        syscall in SOCKET_SYSCALL_NAMES,
      ))
      self.modelCounts.add(items=(syscall, 0, False))
    self.update_InterceptedSyscalls_count()
    # Restore the saved size and position
    if self.settings.get_value('width', 0) and self.settings.get_value('height', 0):
      self.ui.winMain.set_default_size(
        self.settings.get_value('width', -1),
        self.settings.get_value('height', -1))
    if self.settings.get_value('left', 0) and self.settings.get_value('top', 0):
      self.ui.winMain.move(
        self.settings.get_value('left', 0),
        self.settings.get_value('top', 0))
    # Restore visible columns
    saved_visible_columns = self.settings.get_activities_visible_columns()
    if saved_visible_columns is not None:
      for key, (column, menuitem) in self.dict_column_headers.items():
        menuitem.set_active(key in saved_visible_columns)
    # Set ModelFilter
    self.filtered_items = []
    self.ui.filterActivities.set_visible_func(self.check_for_filtered_syscall,
      self.filtered_items)
    # Set counts filter
    self.ui.filterCounts.set_visible_column(self.modelCounts.COL_VISIBILITY)
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

  def loadUI(self):
    """Load the interface UI"""
    self.modelActivities = ModelActivities(self.ui.storeActivities)
    self.modelInterceptedSyscalls = ModelInterceptedSyscalls(
      self.ui.storeInterceptedSyscalls)
    self.modelCounts = ModelCounts(self.ui.storeCounts)
    self.modelFiles = ModelFiles(self.ui.storeFiles)
    self.modelProcesses = ModelProcesses(self.ui.storeProcesses)

    # Associate each TreeViewColumn to the MenuItem used to show/hide
    self.dict_column_headers = {}
    for column, menuitem in (
        ('colActivitiesTimestamp', 'menuitemActivitiesVisibleColumnsTimestamp'),
        ('colActivitiesTime', 'menuitemActivitiesVisibleColumnsTime'),
        ('colActivitiesSyscall', 'menuitemActivitiesVisibleColumnsSyscall'),
        ('colActivitiesFormat', 'menuitemActivitiesVisibleColumnsFormat'),
        ('colActivitiesPID', 'menuitemActivitiesVisibleColumnsPID'),
        ('colActivitiesIP', 'menuitemActivitiesVisibleColumnsIP')):
      self.dict_column_headers[self.ui.get_object(column).get_name()] = (
        self.ui.get_object(column), self.ui.get_object(menuitem))
    # Set cellrenderers alignment
    self.ui.cellActivitiesTimestamp.set_property('xalign', 1.0)
    self.ui.cellActivitiesTime.set_property('xalign', 1.0)
    # Set options menu items value as their column headers
    for key, (tvwcolumn, menuitem) in self.dict_column_headers.items():
      # Set the MenuItem label as the TreeViewColumn header
      menuitem.set_label(tvwcolumn.get_title())
      # Set button-press-event to the Button contained inside the TreeViewColumn
      button = find_button_from_gtktreeviewcolumn(tvwcolumn)
      if button:
        # Set a signal callback to the Button
        button.connect('button-press-event', self.on_tvwcolumn_button_release_event)
    # Set various properties
    self.ui.winMain.set_title(APP_NAME)
    self.ui.winMain.set_icon_from_file(FILE_ICON)
    self.ui.winMain.set_application(self.application)
    self.lblInterceptedSyscalls_descr = self.ui.lblInterceptedSyscalls.get_text()
    # Connect signals from the glade file to the functions with the same name
    self.ui.connect_signals(self)

  def on_winMain_delete_event(self, widget, event):
    """Close the application"""
    # Immediately hide the main window and let the events process to handle
    # an instantly close instead of slowly let GTK to empty the model before
    # the window is effectively destroyed
    self.ui.winMain.hide()
    process_events()
    # Cancel the running thread
    if self.thread_loader and self.thread_loader.isAlive():
      self.thread_loader.cancel()
      self.thread_loader.join()
    self.about.destroy()
    # Save settings for window size, intercepted syscalls and visible columns
    self.settings.set_sizes(self.ui.winMain)
    self.settings.set_intercepted_syscalls(self.modelInterceptedSyscalls)
    self.settings.set_activities_visible_columns(
      [column for column, menuitem in self.dict_column_headers.values()])
    self.settings.set_boolean(SECTION_APPLICATION, 'autoclear',
      self.ui.menuitemAutoClear.get_active())
    self.settings.set_boolean(SECTION_COUNTS, 'only called',
      self.ui.menuitemCountsOnlyCalled.get_active())
    self.settings.set_boolean(SECTION_FILES, 'only existing',
      self.ui.menuitemFilesShowOnlyExisting.get_active())
    self.settings.save()
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
    self.ui.btnStartStop.set_sensitive(len(self.ui.txtProgram.get_text()) > 0)

  def thread_debug_process(self, program):
    """Debug the requested program to trace the syscalls"""
    self.debug_start_time = datetime.datetime.now()
    self.debugger = SyscallTracer(
      options=optparse.Values({
        'fork': True,
        'enter': False,
        'show_ip': True,
        'trace_exec': True,
        'no_stdout': False,
        'pid': None,
        'show_pid': True,
      }),
      program=program,
      ignore_syscall_callback=self.ignore_syscall_callback,
      syscall_callback=self.syscall_callback,
      event_callback=self.event_callback,
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
      if argument.name in FILENAME_ARGUMENTS and argument_text != "''...": 
        GObject.idle_add(self.modelFiles.add, (
          str(syscall.process.pid),
          os.path.basename(argument_text[1:-1]),
          argument_text[1:-1],
          os.path.exists(argument_text[1:-1])))

  def event_callback(self, event):
    """Handle external events like new process execution or child close"""
    def add_process(information, value):
      """Add a process information"""
      now = datetime.datetime.now()
      GObject.idle_add(self.modelProcesses.add, (
        str(event.process.pid),
        (now - self.debug_start_time).total_seconds(),
        now.strftime('%H:%M:%S.%f'),
        information, str(value).strip()))
    
    def add_process_information(item):
      if ':' in item:
        add_process(*item.split(':', 1))

    def get_process_status_details(pid):
      """Get details from process status"""
      dict_result = {}
      status_file = openProc('%s/status' % pid)
      for line in status_file:
        if line.startswith('Uid:'):
          dict_result['uid'] = pwd.getpwuid(int(line[5:].split('\t')[0]))
          dict_result['euid'] = pwd.getpwuid(int(line[5:].split('\t')[1]))
        elif line.startswith('Gid:'):
          dict_result['gid'] = grp.getgrgid(int(line[5:].split('\t')[0]))
          dict_result['egid'] = grp.getgrgid(int(line[5:].split('\t')[1]))
      status_file.close()
      return dict_result

    if isinstance(event, NewProcessEvent):
      # Under Linux the new process phase first fork a new process with the same
      # command line of the starting process then changes its command line
      # Therefore here I skip the NewProcessEvent event and after I add a new
      # process during the ProcessExecution event
      status = None
    elif isinstance(event, ProcessExecution):
      status = _('Process execution')
    elif isinstance(event, ProcessExit):
      status = _('Process exit')
    elif isinstance(event, ProcessSignal):
      status = _('Process signal: %s') % event
    elif isinstance(event, ChildError):
      status = None
      print event
    else:
      status = _('Event: %s') % event
    
    if RUNNING_LINUX and isinstance(event, ProcessExecution):
      add_process(_('Command line'),
        ' '.join(readProcessCmdline(event.process.pid)))
      add_process(_('Current working directory'),
        readProcessLink(event.process.pid, 'cwd'))
      # If the process has a parent PID include it in the details
      if event.process.parent:
        add_process(_('Parent PID'), str(event.process.parent.pid))
      # Add process details
      status_details = get_process_status_details(event.process.pid)
      if status_details.has_key('uid'):
        add_process(_('User ID'), status_details['uid'].pw_uid)
        add_process(_('User name'), status_details['uid'].pw_name)
        add_process(_('User real name'), status_details['uid'].pw_gecos)
      if status_details.has_key('euid'):
        add_process(_('Effective user ID'), status_details['euid'].pw_uid)
        add_process(_('Effective user name'), status_details['euid'].pw_name)
        add_process(_('Effective user real name'), status_details['euid'].pw_gecos)
      if status_details.has_key('gid'):
        add_process(_('Group ID'), status_details['gid'].gr_gid)
        add_process(_('Group name'), status_details['gid'].gr_name)
      if status_details.has_key('egid'):
        add_process(_('Effective group ID'), status_details['egid'].gr_gid)
        add_process(_('Effective group name'), status_details['egid'].gr_name)
    if status:
      add_process(information=_('Status'), value=status)

  def ignore_syscall_callback(self, syscall):
    """Determine if to ignore a callback before it's processed"""
    name = syscall.name
    if syscall.name in self.modelInterceptedSyscalls.syscalls:
      # Process the syscall
      return False
    else:
      # Ignore the syscall
      # print 'ignored syscall %s' % name
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
    self.ui.lblInterceptedSyscalls.set_text(self.lblInterceptedSyscalls_descr % {
      'selected': len(self.modelInterceptedSyscalls.syscalls),
      'total': self.modelInterceptedSyscalls.count(),
    })

  def on_btnOptions_clicked(self, widget):
    """Show the options popup menu"""
    show_popup_menu(self.ui.menuOptions)

  def on_menuitemActivitiesVisibleColumns_toggled(self, widget):
    """Hide or show a column header"""
    for column, menuitem in self.dict_column_headers.values():
      # If both column and menuitem have the same label set column visibility
      if column.get_title() == widget.get_label():
        column.set_visible(widget.get_active())
        break

  def on_tvwcolumn_button_release_event(self, widget, event):
    """Show columns visibility menu on right click"""
    if event.button == Gdk.BUTTON_SECONDARY:
      show_popup_menu(self.ui.menuActivitiesVisibleColumns)

  def on_btnStartStop_toggled(self, widget):
    """Start and stop program tracing"""
    if self.ui.btnStartStop.get_active():
      if self.ui.txtProgram.get_text():
        if self.ui.menuitemAutoClear.get_active():
          self.on_menuitemClear_activate(None)
        # Disable file chooser and set stop icon
        self.ui.txtProgram.set_sensitive(False)
        self.ui.btnProgramOpen.set_sensitive(False)
        self.ui.imgStartStop.set_from_icon_name(Gtk.STOCK_STOP, Gtk.IconSize.BUTTON)
        # Start debugger
        self.thread_loader = DaemonThread(
          target=self.thread_debug_process,
          args=(shlex.split(self.ui.txtProgram.get_text()), )
        )
        self.thread_loader.start()
      else:
        # If no filename was selected then set button status as unpressed
        self.ui.btnStartStop.set_active(False)
    else:
      # Cancel running debugger
      if self.thread_loader:
        self.thread_loader.cancel()
        self.debugger.quit()
        # Restore file chooser and set execute icon
        self.ui.txtProgram.set_sensitive(True)
        self.ui.btnProgramOpen.set_sensitive(True)
        self.ui.imgStartStop.set_from_icon_name(Gtk.STOCK_EXECUTE, Gtk.IconSize.BUTTON)

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
        # Then remove the selected syscall from the filtered syscalls list
        self.filtered_items.remove(self.modelActivities.get_syscall(
          self.ui.filterActivities.convert_iter_to_child_iter(iter)))
        # Filter the results
        self.ui.filterActivities.refilter()

  def on_menuitemActivitiesIgnoreSyscall_activate(self, widget):
    """Remove the selected syscall name from the intercepted syscalls model"""
    self.on_menuitemActivitiesIgnoreUnignoreSyscall(False)

  def on_menuitemActivitiesUnignoreSyscall_activate(self, widget):
    """Add the selected syscall name to the intercepted syscalls model"""
    self.on_menuitemActivitiesIgnoreUnignoreSyscall(True)

  def on_menuitemActivitiesIgnoreUnignoreSyscall(self, status):
    """Add or remove the selected syscall name from the intercepted syscalls model"""
    selection = self.ui.tvwActivities.get_selection()
    if selection:
      model, iter = selection.get_selected()
      if iter:
        # Get the syscall name to ignore/unignore
        selected_syscall = self.modelActivities.get_syscall(
          self.ui.filterActivities.convert_iter_to_child_iter(iter))
        # Cycle each row in the intercepted syscalls model
        for row in self.modelInterceptedSyscalls:
          # If the syscall name for the row is the same then ignore/unignore
          if self.modelInterceptedSyscalls.get_syscall(row) == selected_syscall:
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
    return self.modelActivities.get_syscall(iter) not in self.filtered_items

  def on_btnProgramOpen_clicked(self, widget):
    """Select the program to open"""
    program = show_dialog_fileopen(
      parent=self.ui.winMain,
      title = _("Select a program to execute"))
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
    self.ui.colFilesExisting.set_clickable(not state)
    self.ui.colFilesPID.set_clickable(not state)
    self.ui.colFilesName.set_clickable(not state)
    self.ui.colFilesPath.set_clickable(not state)
    if state:
      self.ui.tvwFiles.set_model(self.ui.filterFiles)
      self.ui.lblInfoBarContent.set_markup(
        _('When <i><b>Show only existing files</b></i> is selected the sorting '
          'by click on the column headers is disabled'))
    else:
      self.ui.tvwFiles.set_model(self.ui.storeFiles)
    self.ui.infobarInformation.set_visible(state)

  def on_infobar1_response(self, widget, response):
    if response == Gtk.ResponseType.CLOSE:
      self.ui.infobarInformation.set_visible(False)
