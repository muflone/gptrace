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

from .base import ModelBase


class ModelProcesses(ModelBase):
    COL_PID = 0
    COL_TIMESTAMP = 1
    COL_TIME = 2
    COL_INFORMATION = 3
    COL_VALUE = 4

    def __init__(self, model):
        super(self.__class__, self).__init__(model)
        # Store the TreeNodes in a dictionary for faster access
        self.dictProcesses = {}

    def add(self, items):
        """Add a new row in the model"""
        if not items[self.COL_PID] in self.dictProcesses.keys():
            # Add a new row as process ID
            super(self.__class__, self).add(items=(
                items[self.COL_PID],
                items[self.COL_TIMESTAMP],
                items[self.COL_TIME],
                items[self.COL_INFORMATION],
                items[self.COL_VALUE],
            ))
            self.dictProcesses[items[self.COL_PID]] = self.model.get_iter(
                self.count() - 1)
        else:
            # Add the items as children of the PID
            self.add_node(self.dictProcesses[items[self.COL_PID]], items=items)

    def get_pid(self, treepath):
        """Get the PID of a row"""
        return self.get_model_data(treepath, self.COL_PID)

    def get_timestamp(self, treepath):
        """Get the timestamp of a row"""
        return self.get_model_data(treepath, self.COL_TIMESTAMP)

    def get_time(self, treepath):
        """Get the time of a row"""
        return self.get_model_data(treepath, self.COL_TIME)

    def get_information(self, treepath):
        """Get the information of a row"""
        return self.get_model_data(treepath, self.COL_INFORMATION)

    def get_value(self, treepath):
        """Get the value of a row"""
        return self.get_model_data(treepath, self.COL_VALUE)
