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

from gi.repository.GdkPixbuf import Pixbuf

from gptrace.constants import *
from gptrace.functions import *
from gptrace.gtkbuilder_loader import GtkBuilderLoader


class AboutWindow(object):
    def __init__(self, win_parent, show=False):
        # Retrieve the translators list
        translators = []
        for line in readlines(FILE_TRANSLATORS, False):
            if ':' in line:
                line = line.split(':', 1)[1]
            line = line.replace('(at)', '@').strip()
            if line not in translators:
                translators.append(line)
        # Load the user interface
        self.ui = GtkBuilderLoader(FILE_UI_ABOUT)
        # Set various properties
        self.ui.dialogAbout.set_program_name(APP_NAME)
        self.ui.dialogAbout.set_version('Version %s' % APP_VERSION)
        self.ui.dialogAbout.set_comments(APP_DESCRIPTION)
        self.ui.dialogAbout.set_website(APP_URL)
        self.ui.dialogAbout.set_copyright(APP_COPYRIGHT)
        self.ui.dialogAbout.set_authors(
            ['%s <%s>' % (APP_AUTHOR, APP_AUTHOR_EMAIL)])
        # self.dialog.set_license_type(Gtk.License.GPL_2_0)
        self.ui.dialogAbout.set_license(
            '\n'.join(readlines(FILE_LICENSE, True)))
        self.ui.dialogAbout.set_translator_credits('\n'.join(translators))
        # Retrieve the external resources links
        for line in readlines(FILE_RESOURCES, False):
            resource_type, resource_url = line.split(':', 1)
            self.ui.dialogAbout.add_credit_section(resource_type,
                                                   (resource_url,))
        icon_logo = Pixbuf.new_from_file(FILE_ICON)
        self.ui.dialogAbout.set_logo(icon_logo)
        self.ui.dialogAbout.set_transient_for(win_parent)
        # Optionally show the dialog
        if show:
            self.show()

    def show(self):
        """Show the About dialog"""
        self.ui.dialogAbout.run()
        self.ui.dialogAbout.hide()

    def destroy(self):
        """Destroy the About dialog"""
        self.ui.dialogAbout.destroy()
