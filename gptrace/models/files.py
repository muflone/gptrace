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


class ModelFiles(ModelAbstract):
    COL_PID = 0
    COL_FILEPATH = 1
    COL_EXISTING = 2

    def __init__(self, model):
        super(self.__class__, self).__init__(model)
        # Store the files in a list for each process
        self.processes = {}

    def add_data(self, item):
        """Add a new row to the model if it doesn't exist"""
        super(self.__class__, self).add_data(item)
        if item.pid not in self.rows:
            # Add a new process
            process_row = self.model.append(None, (
                item.pid,
                None,
                True
            ))
            self.rows[item.pid] = process_row
            # Create a new list for the files for the current process
            self.processes[item.pid] = []
        else:
            # Get the existing process iter
            process_row = self.rows[item.pid]
        # Add the file under the process if not already existing
        if item.file_path and item.file_path not in self.processes[item.pid]:
            self.model.append(process_row, (
                None,
                item.file_path,
                item.existing))
            self.processes[item.pid].append(item.file_path)

    def clear(self):
        """Clear the model"""
        self.processes.clear()
        return super(self.__class__, self).clear()
