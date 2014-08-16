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

class ModelBase(object):
  def __init__(self, model):
    """Initialize the object with the model"""
    self.model = model

  def path_from_iter(self, treeiter):
    """Return a path from an iter"""
    return self.model.get_path(treeiter)
  
  def path_from_row(self, treerow):
    """Return a path from a treerow"""
    return isinstance(treerow, Gtk.TreeModelRow) and treerow.path or treerow
  
  def row_from_iter(self, treeiter):
    """Return a model row from an iter"""
    return self.model[treeiter]

  def get_model_data(self, treepath, column):
    """Return a specific column from a treepath"""
    return self.model[self.path_from_row(treepath)][column]

  def set_model_data(self, treepath, column, value):
    """Set a specific column from a treepath"""
    self.model[self.path_from_row(treepath)][column] = value

  def add(self, items):
    """Add a new treerow to the model"""
    if isinstance(self.model, Gtk.ListStore):
      self.model.append(items)
    else:
      self.model.append(None, items)
    return False

  def remove(self, treeiter):
    """Remove a treerow from the model"""
    self.model.remove(treeiter)

  def clear(self):
    """Empty the model"""
    return self.model.clear()

  def count(self):
    """Return the number of rows into the model"""
    return len(self.model)

  def __iter__(self):
    """Iter over the model rows"""
    return iter(self.model)

  def add_node(self, parent, items):
    """Add a new child treerow to the model"""
    return self.model.append(parent, items)
