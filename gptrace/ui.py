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

from gi.repository import Gtk
from gi.repository import Gio
from gi.repository import GObject
from gptrace.constants import *
from gptrace.functions import *
from gptrace.settings import Settings
from gptrace.model_results import ModelResults
from gptrace.model_intercepted_syscalls import ModelInterceptedSyscalls
from gptrace.about import AboutWindow
from daemon_thread import DaemonThread
from syscall_tracer import SyscallTracer

from ptrace.syscall import SYSCALL_NAMES, SYSCALL_PROTOTYPES, FILENAME_ARGUMENTS, SOCKET_SYSCALL_NAMES
from ptrace.ctypes_tools import formatAddress

import optparse
import datetime

class MainWindow(object):
  def __init__(self, application, settings):
    self.application = application
    self.loadUI()
    self.settings = settings
    # Restore the intercepted syscalls list from settings
    saved_syscalls = settings.get_intercepted_syscalls()
    # Load all the available syscall names
    for syscall in SYSCALL_NAMES.values():
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
      )
    )
    self.update_InterceptedSyscalls_count()
    # Restore the saved size and position
    if self.settings.get_value('width', 0) and self.settings.get_value('height', 0):
      self.winMain.set_default_size(
        self.settings.get_value('width', -1),
        self.settings.get_value('height', -1))
    if self.settings.get_value('left', 0) and self.settings.get_value('top', 0):
      self.winMain.move(
        self.settings.get_value('left', 0),
        self.settings.get_value('top', 0))
    # Load the others dialogs
    self.about = AboutWindow(self.winMain, False)
    self.thread_loader = None
    self.debugger = None

  def run(self):
    "Show the UI"
    self.winMain.show_all()

  def loadUI(self):
    "Load the interface UI"
    builder = Gtk.Builder()
    builder.add_from_file(FILE_UI_MAIN)
    # Obtain widget references
    self.winMain = builder.get_object("winMain")
    self.modelResults = ModelResults(builder.get_object('storeResults'))
    self.modelInterceptedSyscalls = ModelInterceptedSyscalls(
      builder.get_object('storeInterceptedSyscalls'))
    self.filechooserProgram = builder.get_object('filechooserProgram')
    self.lblInterceptedSyscalls = builder.get_object('lblInterceptedSyscalls')
    # Set cellrenderers alignment
    builder.get_object('cellTimestamp').set_property('xalign', 1.0)
    builder.get_object('cellTime').set_property('xalign', 1.0)
    # Set various properties
    self.winMain.set_title(APP_NAME)
    self.winMain.set_icon_from_file(FILE_ICON)
    self.winMain.set_application(self.application)
    self.lblInterceptedSyscalls_descr = self.lblInterceptedSyscalls.get_text()
    # Connect signals from the glade file to the functions with the same name
    builder.connect_signals(self)

  def on_winMain_delete_event(self, widget, event):
    "Close the application"
    # Cancel the running thread
    if self.thread_loader and self.thread_loader.isAlive():
      self.thread_loader.cancel()
      self.thread_loader.join()
    self.about.destroy()
    # Save settings for window size and intercepted syscalls list
    self.settings.set_sizes(self.winMain)
    self.settings.set_intercepted_syscalls(self.modelInterceptedSyscalls)
    self.settings.save()
    self.winMain.destroy()
    self.application.quit()

  def on_btnAbout_clicked(self, widget):
    "Show the about dialog"
    self.about.show()

  def on_filechooserProgram_file_set(self, widget):
    "Select the program to execute"
    if self.filechooserProgram.get_filename():
      self.thread_loader = DaemonThread(
        target=self.thread_debug_process,
        args=(self.filechooserProgram.get_filename(), )
      )
      self.thread_loader.start()

  def thread_debug_process(self, program):
    self.debug_start_time = datetime.datetime.now()
    self.debugger = SyscallTracer(
      options=optparse.Values(),
      program=program,
      ignore_syscall_callback=self.ignore_syscall_callback,
      syscall_callback=self.syscall_callback,
      event_callback=self.event_callback)
    self.debugger.main()
    # Cancel the running thread
    #  if self.thread_loader.cancelled:
    #    print 'abort'
    #    break
    return True

  def syscall_callback(self, syscall):
    """Add the syscall to the results model"""
    # print syscall, syscall.instr_pointer, syscall.format()
    now = datetime.datetime.now()
    GObject.idle_add(self.modelResults.add, (
      (now - self.debug_start_time).total_seconds(),
      now.strftime('%H:%M:%S.%f'),
      syscall.name,
      syscall.process.pid,
      formatAddress(syscall.instr_pointer)
    ))

  def event_callback(self, event):
    print 'event', type(event), event

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
    self.lblInterceptedSyscalls.set_text(self.lblInterceptedSyscalls_descr % (
      len(self.modelInterceptedSyscalls.syscalls),
      self.modelInterceptedSyscalls.count(),
    ))
