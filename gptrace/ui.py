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
from gptrace.model_syscalls import ModelSyscalls
from gptrace.about import AboutWindow
from daemon_thread import DaemonThread
from syscall_tracer import SyscallTracer

import optparse
import datetime

class MainWindow(object):
  def __init__(self, application, settings):
    self.application = application
    self.loadUI()
    self.settings = settings
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
    self.model = ModelSyscalls(builder.get_object('storeSyscalls'))
    self.tvwItems = builder.get_object('tvwSyscalls')
    self.filechooserProgram = builder.get_object('filechooserProgram')
    # Set cellrenderers alignment
    builder.get_object('cellTimestamp').set_property('xalign', 1.0)
    builder.get_object('cellTime').set_property('xalign', 1.0)
    # Set various properties
    self.winMain.set_title(APP_NAME)
    self.winMain.set_icon_from_file(FILE_ICON)
    self.winMain.set_application(self.application)
    # Connect signals from the glade file to the functions with the same name
    builder.connect_signals(self)

  def on_winMain_delete_event(self, widget, event):
    "Close the application"
    # Cancel the running thread
    if self.thread_loader and self.thread_loader.isAlive():
      self.thread_loader.cancel()
      self.thread_loader.join()
    self.about.destroy()
    self.settings.set_sizes(self.winMain)
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
      syscall_callback=self.syscall_callback,
      event_callback=self.event_callback)
    self.debugger.main()
    # Cancel the running thread
    #  if self.thread_loader.cancelled:
    #    print 'abort'
    #    break
    return True

  def syscall_callback(self, syscall):
    now = datetime.datetime.now()
    GObject.idle_add(self.model.add,
      (now - self.debug_start_time).total_seconds(),
      now.strftime('%H:%M:%S.%f'),
      syscall.name,
      0)

  def event_callback(self, event):
    print event
