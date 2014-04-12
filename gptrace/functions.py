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

import struct
import socket
from gettext import gettext as _
from gi.repository import Gtk
from gptrace.constants import *

def show_message_dialog_yesno(winParent, message, title, default_response):
  "Show a GtkMessageDialog with yes and no buttons"
  dialog = Gtk.MessageDialog(
    parent=winParent,
    flags=Gtk.DialogFlags.MODAL,
    type=Gtk.MessageType.QUESTION,
    buttons=Gtk.ButtonsType.YES_NO,
    message_format=message
  )
  dialog.set_title(title)
  if default_response:
    dialog.set_default_response(default_response)
  response = dialog.run()
  dialog.destroy()
  return response

def readlines(filename, empty_lines = False):
  result = []
  with open(filename) as f:
    for line in f.readlines():
      line = line.strip()
      if line or empty_lines:
        result.append(line)
    f.close()
  return result

__all__ = [
  'show_message_dialog_yesno',
  'readlines',
  '_'
]
