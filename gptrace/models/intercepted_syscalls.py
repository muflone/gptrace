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

from .base import ModelBase

class ModelInterceptedSyscalls(ModelBase):
  COL_CHECKED = 0
  COL_SYSCALL = 1
  COL_RESULT = 2
  COL_ARGUMENTS = 3
  COL_FILENAME_ARGUMENTS = 4
  COL_SOCKET_FUNCTION = 5

  def __init__(self, model):
    """Initialize the model and set the syscalls list to empty list"""
    super(self.__class__, self).__init__(model)
    self.clear()

  def add(self, items):
    """Add a new row in the model"""
    super(self.__class__, self).add(items)
    # If the checked status is True add the syscall name to the syscalls list
    if items[self.COL_CHECKED]:
      self.syscalls.append(items[self.COL_SYSCALL])
    return False

  def clear(self):
    """Remove every items in the model and clear the syscalls list"""
    super(self.__class__, self).clear()
    self.syscalls = []
    return False

  def get_checked(self, treepath):
    """Get the checked status"""
    return self.get_model_data(treepath, self.COL_CHECKED)

  def set_checked(self, treepath, value):
    """Set the checked status and insert/remove from the syscalls list"""
    name = self.get_syscall(treepath)
    if value and name not in self.syscalls:
      self.syscalls.append(name)
    elif not value and name in self.syscalls:
      self.syscalls.remove(name)
    return self.set_model_data(treepath, self.COL_CHECKED, value)

  def toggle_checked(self, treepath):
    """Toggle the checked status"""
    return self.set_checked(treepath, not self.get_checked(treepath))

  def get_syscall(self, treepath):
    """Get the syscall name"""
    return self.get_model_data(treepath, self.COL_SYSCALL)

  def get_result_type(self, treepath):
    """Get the result type"""
    return self.get_model_data(treepath, self.COL_RESULT)

  def get_arguments(self, treepath):
    """Get the arguments list"""
    return self.get_model_data(treepath, self.COL_ARGUMENTS)

  def get_has_filename_arguments(self, treepath):
    """Get if any arguments is filename/pathname"""
    return self.get_model_data(treepath, self.COL_FILENAME_ARGUMENTS)

  def get_socket_function(self, treepath):
    """Get if the function is used by sockets"""
    return self.get_model_data(treepath, self.COL_SOCKET_FUNCTION)
