#!/bin/bash
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

PO_DIR="po"
POT_FILE="${PO_DIR}/gptrace.pot"
XGETTEXT_OPTIONS="--join-existing
  --add-location --omit-header
  --keyword=N_ --keyword=_
  --output "${POT_FILE}""
CURRENT_DATETIME="$(date +'%F %T %z')"
AVAILABLE_LANGUAGES="en_US it"
LOCALE_DIR="locale"

# Create po directory if needed
if ! [ -d "${PO_DIR}" ]
then
  mkdir "${PO_DIR}"
fi

# Create .pot file if needed
if ! [ -f "${POT_FILE}" ]
then
  cat > "${POT_FILE}" << EOF
# gpTrace
# Trace the activities of an external application.
# Copyright (C) 2014 Fabio Castelli (Muflone) <webreg(at)vbsimple.net>
# This file is distributed under the same license as the gpTrace package.
# X translation for gpTrace.
#
#, fuzzy
msgid ""
msgstr ""
"Project-Id-Version: gpTrace\n"
"Report-Msgid-Bugs-To: https://github.com/muflone/gptrace/issues \n"
"POT-Creation-Date: ${CURRENT_DATETIME}\n"
"PO-Revision-Date: YEAR-MO-DA HO:MI+ZONE\n"
"Last-Translator: FULL NAME <EMAIL@ADDRESS>\n"
"Language-Team: https://www.transifex.com/projects/p/gptrace/ \n"
"Language: \n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=CHARSET\n"
"Content-Transfer-Encoding: 8bit\n"
EOF
fi

# Extracting translations from UI files
echo "Adding GUI files to translations..."
for gladefile in ui/*.glade ui/*.ui
do
  # Extract translations from Glade files
  intltool-extract --type=gettext/glade --quiet "${gladefile}"
  echo -ne " * ${gladefile}\t"
  if [ -f "${gladefile}.h" ]
  then
    if [ -s "${gladefile}.h" ]
    then
      # File added to translations
      echo xgettext ${XGETTEXT_OPTIONS} "${gladefile}.h"
      xgettext ${XGETTEXT_OPTIONS} "${gladefile}.h"
      echo "OK"
    else
      # File not added to translations
      echo "NO"
    fi
    rm "${gladefile}.h"
  fi
done
echo -e "done.\n"

# Extract translations from source files
echo "Adding source files to translations..."
xgettext ${XGETTEXT_OPTIONS} gptrace/*.py gptrace/*/*.py
echo -e "done.\n"

# Prepare locales directory
[ -d "${LOCALE_DIR}" ] && rm -rf "${LOCALE_DIR}"
mkdir "${LOCALE_DIR}"

# Create the .po file from a .pot file or update it
for language in ${AVAILABLE_LANGUAGES}
do
  PO_FILE="po/${language}.po"
  if [ -f "${PO_FILE}" ]
  then
    # If any existing translated file exists then it will be updated with the
    # new translations
    msgmerge --backup=off --no-fuzzy-matching --update "${PO_FILE}" "${POT_FILE}"
  else
    # If no existing translated file exists then a new file will be created
    # based on the .pot file
    msginit --no-translator --input="${POT_FILE}" --locale="${language}" \
      --output-file="${PO_FILE}"
  fi
  MO_DIR="${LOCALE_DIR}/${language}/LC_MESSAGES"
  # Extract the translations from a .po to a .mo file
  mkdir -p "${MO_DIR}"
  msgfmt --output-file="${MO_DIR}/gptrace.mo" "${PO_FILE}"
done
