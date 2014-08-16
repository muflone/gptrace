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

class ModelFiles(ModelBase):
  COL_PID = 0
  COL_FILENAME = 1
  COL_FILEPATH = 2
  COL_EXISTING = 3
  
  KEY_ITER = 'iter'
  KEY_FILES = 'files'

  def __init__(self, model):
    super(self.__class__, self).__init__(model)
    # Store the TreeNodes in a dictionary for faster access
    self.dictProcesses = {}

  def add(self, items):
    """Add a new row in the model"""
    if not items[self.COL_PID] in self.dictProcesses.keys():
      # Add a new row as process ID
      super(self.__class__, self).add(
        items=(items[self.COL_PID], None, None, True))
      self.dictProcesses[items[self.COL_PID]] = {
        self.KEY_ITER: self.model.get_iter(self.count() - 1),
        self.KEY_FILES: []
      }
    # Add the items as children of the PID
    subitems = [None, ]
    subitems.extend(items[1:])
    pid_process = self.dictProcesses[items[self.COL_PID]]
    if not items[self.COL_FILEPATH] in pid_process[self.KEY_FILES]:
      # The requested filepath doesn't exist in the saved list of processes
      # therefore it will be appended under the PID node
      self.add_node(pid_process[self.KEY_ITER], items=subitems)
      pid_process[self.KEY_FILES].append(items[self.COL_FILEPATH])

  def get_filename(self, treepath):
    """Get the filename of a row"""
    return self.get_model_data(treepath, self.COL_FILENAME)

  def get_filepath(self, treepath):
    """Get the filepath of a row"""
    return self.get_model_data(treepath, self.COL_FILEPATH)

  def clear(self):
    """Empty the model"""
    self.dictProcesses.clear()
    return super(self.__class__, self).clear()
