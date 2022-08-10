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

from gettext import dgettext as gettext_with_domain
from gettext import gettext as _
import os.path

from gi.repository import Gtk

from gptrace.constants import DIR_UI


def show_dialog_fileopen(parent, title):
    """Show a FileChooserDialog with open and cancel buttons"""
    dialog = Gtk.FileChooserDialog(
        parent=parent,
        flags=Gtk.DialogFlags.MODAL,
        type=Gtk.WindowType.TOPLEVEL,
        buttons=(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                 Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
    )
    if title:
        dialog.set_title(title)
    if dialog.run() == Gtk.ResponseType.OK:
        result = dialog.get_filename()
    else:
        result = None
    dialog.destroy()
    return result


def readlines(filename, empty_lines=False):
    """
    Read all the text in the specified filename, allowing to skip empty lines
    """
    result = []
    with open(filename) as f:
        for line in f.readlines():
            line = line.strip()
            if line or empty_lines:
                result.append(line)
        f.close()
    return result


def process_events():
    """Process every pending GTK+ event"""
    while Gtk.events_pending():
        Gtk.main_iteration()


def find_button_from_gtktreeviewcolumn(tvwcolumn):
    """Find the Button widget contained inside a TreeViewColumn"""
    # Save the column title to restore it later
    column_title = tvwcolumn.get_title()
    # Create a Label widget and add it to the TreeViewColumn
    label_widget = Gtk.Label('')
    tvwcolumn.set_widget(label_widget)
    # Iter every parent until a Button is found
    widget = label_widget
    while not isinstance(widget, Gtk.Button):
        widget = widget.get_parent()
    # Remove the Label from the TreeViewColumn and restore the column title
    tvwcolumn.set_widget(None)
    tvwcolumn.set_title(column_title)
    label_widget.destroy()
    return widget


def GTK30_(message, context=None):
    """Get a translated message from GTK+ 3 domain"""
    return gettext_with_domain('gtk30',
                               context and '%s\x04%s' % (
                                   context, message) or message)


def get_ui_file(filename):
    """Return the full path of a Glade/UI file"""
    return os.path.join(DIR_UI, filename)


__all__ = [
    'show_dialog_fileopen',
    'readlines',
    'process_events',
    'find_button_from_gtktreeviewcolumn',
    '_',
    'GTK30_',
    'get_ui_file'
]
