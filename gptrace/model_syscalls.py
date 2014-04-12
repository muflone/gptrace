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
from gptrace.constants import *

class ModelSyscalls(object):
  COL_ITEM = 0
  def __init__(self, model):
    self.model = model
    self.index = 0

  def path_from_iter(self, treeiter):
    return type(treeiter) is Gtk.TreeModelRow and treeiter.path or treeiter

  def get_model_data(self, treeiter, column):
    return self.model[self.path_from_iter(treeiter)][column]

  def set_model_data(self, treeiter, column, value):
    self.model[self.path_from_iter(treeiter)][column] = value

  def add(self, item):
    return self.model.append((
      item
    ))

  def remove(self, treeiter):
    self.model.remove(treeiter)

  def clear(self):
    return self.model.clear()

  def count(self):
    return len(self.model)

  def __iter__(self):
    return iter(self.model)
