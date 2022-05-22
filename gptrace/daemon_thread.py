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

from threading import Thread

from gi.repository import GObject
from gi.repository import Gdk


class DaemonThread(Thread):
    def __init__(self, target, args=()):
        GObject.threads_init()
        Gdk.threads_init()
        super(self.__class__, self).__init__(target=target, args=args)
        self.daemon = True
        self.cancelled = False

    def cancel(self):
        self.cancelled = True
