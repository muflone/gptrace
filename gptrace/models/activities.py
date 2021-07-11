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


class ModelActivities(ModelBase):
    COL_TIMESTAMP = 0
    COL_TIME = 1
    COL_SYSCALL = 2
    COL_FORMAT = 3
    COL_PID = 3
    COL_IP = 4

    def __init__(self, model):
        super(self.__class__, self).__init__(model)

    def get_timestamp(self, treepath):
        """Get the timestamp of a row"""
        return self.get_model_data(treepath, self.COL_TIMESTAMP)

    def get_time(self, treepath):
        """Get the relative time of a row"""
        return self.get_model_data(treepath, self.COL_TIME)

    def get_syscall(self, treepath):
        """Get the syscall of a row"""
        return self.get_model_data(treepath, self.COL_SYSCALL)

    def get_format(self, treepath):
        """Get the format of a row"""
        return self.get_model_data(treepath, self.COL_FORMAT)

    def get_pid(self, treepath):
        """Get the PID of a row"""
        return self.get_model_data(treepath, self.COL_PID)

    def get_ip(self, treepath):
        """Get the instruction pointer of a row"""
        return self.get_model_data(treepath, self.COL_IP)
