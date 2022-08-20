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

from .abstract import ModelAbstract


class ModelCounts(ModelAbstract):
    COL_SYSCALL = 0
    COL_COUNT = 1
    COL_VISIBILITY = 2

    def add_data(self, item):
        """Add a new row to the model if it doesn't exist"""
        super(self.__class__, self).add_data(item)
        if item.syscall not in self.rows:
            new_row = self.model.append((
                item.syscall,
                item.count,
                item.visibility
            ))
            self.rows[item.syscall] = new_row

    def increment_count(self, syscall):
        """Increment the count by 1 for the requested syscall"""
        treeiter = self.get_iter(syscall)
        self.model[treeiter][self.COL_COUNT] = (
                self.model[treeiter][self.COL_COUNT] + 1)
        self.model[treeiter][self.COL_VISIBILITY] = True

    def clear_values(self):
        """Set the count of all items to zero"""
        for treeiter in self.rows.values():
            self.model[treeiter][self.COL_COUNT] = 0
            self.model[treeiter][self.COL_VISIBILITY] = False
