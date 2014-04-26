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

import os
import os.path
import optparse
import time
import ConfigParser
from gptrace.functions import *
from gptrace.constants import *

SECTION_MAINWIN = 'main window'
SECTION_APPLICATION = 'application'

class Settings(object):
  def __init__(self):
    self.settings = {}
    self.model = None

    # Command line options and arguments
    parser = optparse.OptionParser(usage='usage: %prog [options]')
    parser.set_defaults(verbose_level=VERBOSE_LEVEL_NORMAL)
    parser.add_option('-v', '--verbose', dest='verbose_level',
                      action='store_const', const=VERBOSE_LEVEL_MAX,
                      help='show error and information messages')
    parser.add_option('-q', '--quiet', dest='verbose_level',
                      action='store_const', const=VERBOSE_LEVEL_QUIET,
                      help='hide error and information messages')
    (self.options, self.arguments) = parser.parse_args()
    # Parse settings from the configuration file
    self.config = ConfigParser.RawConfigParser()
    # Allow saving in case sensitive (useful for machine names)
    self.config.optionxform = str
    # Determine which filename to use for settings
    self.filename = FILE_SETTINGS_NEW
    if self.filename:
      self.logText('Loading settings from %s' % self.filename, VERBOSE_LEVEL_MAX)
      self.config.read(self.filename)

  def load(self):
    """Load window settings"""
    if self.config.has_section(SECTION_MAINWIN):
      self.logText('Retrieving window settings', VERBOSE_LEVEL_MAX)
      # Retrieve window position and size
      if self.config.has_option(SECTION_MAINWIN, 'left'):
        self.settings['left'] = self.config.getint(SECTION_MAINWIN, 'left')
      if self.config.has_option(SECTION_MAINWIN, 'top'):
        self.settings['top'] = self.config.getint(SECTION_MAINWIN, 'top')
      if self.config.has_option(SECTION_MAINWIN, 'width'):
        self.settings['width'] = self.config.getint(SECTION_MAINWIN, 'width')
      if self.config.has_option(SECTION_MAINWIN, 'height'):
        self.settings['height'] = self.config.getint(SECTION_MAINWIN, 'height')

  def get_value(self, name, default=None):
    return self.settings.get(name, default)

  def set_sizes(self, winParent):
    """Save configuration for main window"""
    # Main window settings section
    self.logText('Saving window settings', VERBOSE_LEVEL_MAX)
    if not self.config.has_section(SECTION_MAINWIN):
      self.config.add_section(SECTION_MAINWIN)
    # Window position
    position = winParent.get_position()
    self.config.set(SECTION_MAINWIN, 'left', position[0])
    self.config.set(SECTION_MAINWIN, 'top', position[1])
    # Window size
    size = winParent.get_size()
    self.config.set(SECTION_MAINWIN, 'width', size[0])
    self.config.set(SECTION_MAINWIN, 'height', size[1])

  def get_intercepted_syscalls(self):
    """Get the intercepted syscalls list"""
    results = None
    if self.config.has_option(SECTION_APPLICATION, 'intercepted syscalls'):
      results = self.config.get(
        SECTION_APPLICATION, 'intercepted syscalls').split(',')
    return results

  def set_intercepted_syscalls(self, model):
    """Save the intercepted syscalls list"""
    if not self.config.has_section(SECTION_APPLICATION):
      self.config.add_section(SECTION_APPLICATION)
    self.config.set(SECTION_APPLICATION, 'intercepted syscalls', 
      ','.join(model.syscalls))

  def save(self):
    """Save the whole configuration"""
    # Always save the settings in the new configuration file
    file_settings = open(FILE_SETTINGS_NEW, mode='w')
    self.logText('Saving settings to %s' % FILE_SETTINGS_NEW, VERBOSE_LEVEL_MAX)
    self.config.write(file_settings)
    file_settings.close()

  def logText(self, text, verbose_level=VERBOSE_LEVEL_NORMAL):
    """Print a text with current date and time based on verbose level"""
    if verbose_level <= self.options.verbose_level:
      print '[%s] %s' % (time.strftime('%Y/%m/%d %H:%M:%S'), text)
