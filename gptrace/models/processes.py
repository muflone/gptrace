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


class ModelProcesses(ModelAbstract):
    COL_PID = 0
    COL_TIMESTAMP = 1
    COL_TIME = 2
    COL_INFORMATION = 3
    COL_VALUE = 4

    def __init__(self, model):
        super(self.__class__, self).__init__(model)
        # Store the TreeNodes in a dictionary for faster access
        self.dictProcesses = {}

    def add_data(self, item):
        """Add a new row to the model if it doesn't exist"""
        super(self.__class__, self).add_data(item)
        if item.pid not in self.rows:
            # Add a new process
            process_row = self.model.append(None, (
                item.pid,
                item.timestamp,
                item.time,
                item.information,
                item.value))
            self.rows[item.pid] = process_row
        else:
            # Get the existing process iter
            process_row = self.rows[item.pid]
            # Add the information under the process
            self.model.append(process_row, (
                item.pid,
                item.timestamp,
                item.time,
                item.information,
                item.value))
