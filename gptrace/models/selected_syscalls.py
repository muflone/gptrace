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


class ModelSelectedSyscalls(ModelAbstract):
    COL_CHECKED = 0
    COL_SYSCALL = 1
    COL_RESULT = 2
    COL_ARGUMENTS = 3
    COL_FILENAME_ARGUMENTS = 4
    COL_SOCKET_FUNCTION = 5

    def __init__(self, model):
        """Initialize the model and set the syscalls list to empty list"""
        super(self.__class__, self).__init__(model)
        self.syscalls = None
        self.clear()

    def add_data(self, item):
        """Add a new row to the model if it doesn't exist"""
        super(self.__class__, self).add_data(item)
        if item.syscall not in self.rows:
            new_row = self.model.append((
                item.checked,
                item.syscall,
                item.return_type,
                item.arguments,
                item.is_for_file,
                item.is_for_socket
            ))
            self.rows[item.syscall] = new_row
        # If the checked status is True add the syscall name to the
        # syscalls list
        if item.checked:
            self.syscalls.append(item.syscall)

    def clear(self):
        """Remove every item in the model and clear the syscalls list"""
        super(self.__class__, self).clear()
        self.syscalls = []
        return False

    def set_checked(self, treeiter, value):
        """Set the checked status and insert/remove from the syscalls list"""
        name = self.get_syscall(treeiter)
        if value and name not in self.syscalls:
            self.syscalls.append(name)
        elif not value and name in self.syscalls:
            self.syscalls.remove(name)
        self.model[treeiter][self.COL_CHECKED] = value

    def toggle_checked(self, treeiter):
        """Toggle the checked status"""
        status = not self.model[treeiter][self.COL_CHECKED]
        self.model[treeiter][self.COL_CHECKED] = status
        if status:
            self.syscalls.append(self.model[treeiter][self.COL_SYSCALL])
        else:
            self.syscalls.remove(self.model[treeiter][self.COL_SYSCALL])

    def get_syscall(self, treeiter):
        """Get the syscall name"""
        return self.model[treeiter][self.COL_SYSCALL]

    def get_has_filename_arguments(self, treeiter):
        """Get if any arguments is filename/pathname"""
        return self.model[treeiter][self.COL_FILENAME_ARGUMENTS]

    def get_socket_function(self, treeiter):
        """Get if the function is used by sockets"""
        return self.model[treeiter][self.COL_SOCKET_FUNCTION]
