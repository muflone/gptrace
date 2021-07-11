##
#     Project: gpTrace
# Description: Trace the activities of an external application
#      Author: Fabio Castelli (Muflone) <muflone@muflone.com>
#   Copyright: 2014-2021 Fabio Castelli
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

from gi.repository import Gtk


class GtkBuilderLoader(object):
    def __init__(self, *ui_files):
        """Load one or more ui files for GtkBuilder"""
        self.builder = Gtk.Builder()
        for ui_filename in ui_files:
            self.builder.add_from_file(ui_filename)
        self.__widgets = {}

    def __getattr__(self, key):
        """Get a widget from GtkBuilder using class member name"""
        if key not in self.__widgets:
            self.__widgets[key] = self.builder.get_object(key)
            assert (self.__widgets[key])
        return self.__widgets[key]

    def get_object(self, key):
        """Get a widget from GtkBuilder using a method"""
        return self.__getattr__(key)

    def connect_signals(self, handlers):
        """Connect all the Gtk signals to a group of handlers"""
        self.builder.connect_signals(handlers)
