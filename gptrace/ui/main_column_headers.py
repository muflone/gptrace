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

class ShowHideColumnHeaders(object):
    def __init__(self, get_object, settings):
        self.column_headers = {}
        self.get_object = get_object
        self.settings = settings

    def add_columns_to_section(self, section, column, menu, menuitem):
        """Add a GtkTreeViewColumn, a GtkMenu and a GtkMenuItem to a section"""
        columns = {}
        columns[column] = (self.get_object(column),
                           self.get_object(menu), self.get_object(menuitem))
        if section not in self.column_headers:
            self.column_headers[section] = []
        self.column_headers[section].append(columns)

    def load_visible_columns(self, section):
        """Load the visible columns from the settings"""
        visible_columns = self.settings.get_visible_columns(section)
        if visible_columns is not None:
            for items in self.column_headers[section]:
                for column_name, (column, menu, menuitem) in items.items():
                    menuitem.set_active(column_name in visible_columns)

    def save_visible_columns(self, section):
        """Save the visible columns to the settings"""
        self.settings.set_visible_columns(section,
                                          [item.values()[0][0] for item in
                                           self.column_headers[section]])

    def get_sections(self):
        """Return all the available sections"""
        return self.column_headers.keys()

    def get_values(self, section):
        """Return all the widgets for a section"""
        return [list(item.values())[0]
                for item in self.column_headers[section]]
