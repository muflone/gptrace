##
#     Project: gpTrace
# Description: Trace the activities of an external application
#      Author: Fabio Castelli (Muflone) <webreg@vbsimple.net>
#   Copyright: 2014 Fabio Castelli
#     License: GPL-2+
#  This program is free software; you can redistribute it and/or modify it
#  under the terms of the GNU General Public License as published by the Free
#  Software Foundation; either version 2 of the License, or (at your option)
#  any later version.
#
#  This program is distributed in the hope that it will be useful, but WITHOUT
#  ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
#  FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
#  more details.
#  You should have received a copy of the GNU General Public License along
#  with this program; if not, write to the Free Software Foundation, Inc.,
#  51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA
##

from gi.repository import Gtk

from .base import ModelBase

class ModelCounts(ModelBase):
  COL_SYSCALL = 0
  COL_COUNT = 1

  def __init__(self, model):
    super(self.__class__, self).__init__(model)
    # Store the ListStore rows in a dictionary for faster access
    self.dictSyscalls = {}

  def add(self, items):
    """Add a new row in the model"""
    super(self.__class__, self).add(items)
    self.dictSyscalls[items[self.COL_SYSCALL]] = self.model[self.count() - 1]

  def get_syscall(self, treepath):
    """Get the syscall of a row"""
    return self.get_model_data(treepath, self.COL_SYSCALL)

  def get_count(self, treepath):
    """Get the count of a row"""
    return self.get_model_data(treepath, self.COL_COUNT)

  def increment_count(self, syscall):
    """Increment the count by 1 for the requested syscall"""
    model_row = self.dictSyscalls[syscall]
    self.set_model_data(model_row, self.COL_COUNT,
      self.get_model_data(model_row, self.COL_COUNT) + 1)
    
  def clear_values(self):
    """Set the count of all items to zero"""
    for model_row in self.dictSyscalls.values():
      self.set_model_data(model_row, self.COL_COUNT, 0)
