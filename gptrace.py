#!/usr/bin/env python
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

import gettext
import locale

from gptrace.app import Application
from gptrace.constants import *
from gptrace.settings import Settings

if __name__ == '__main__':
    # Load domain for translation
    for module in (gettext, locale):
        module.bindtextdomain(DOMAIN_NAME, DIR_LOCALE)
        module.textdomain(DOMAIN_NAME)

    # Load the settings from the configuration file
    settings = Settings()
    settings.load()

    # Start the application
    app = Application(settings)
    app.run(None)
