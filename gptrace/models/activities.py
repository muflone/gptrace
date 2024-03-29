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


class ModelActivities(ModelAbstract):
    COL_TIMESTAMP = 0
    COL_TIME = 1
    COL_SYSCALL = 2
    COL_FORMAT = 3
    COL_PID = 3
    COL_IP = 4

    def add_data(self, item):
        """Add a new row to the model if it doesn't exist"""
        super(self.__class__, self).add_data(item)
        new_row = self.model.append((
            item.timestamp,
            item.time,
            item.syscall,
            item.format,
            item.pid,
            item.ip
        ))
        self.rows[len(self.rows)] = new_row

    def get_syscall(self, treeiter):
        """Get the syscall of a row"""
        return self.model[treeiter][self.COL_SYSCALL]
