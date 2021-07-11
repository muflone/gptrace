gpTrace
=======
**Description:** Trace the activities of an external application.

**Copyright:** 2014-2021 Fabio Castelli (Muflone) <muflone(at)muflone.com>

**License:** GPL-3+

**Source code:** https://github.com/muflone/gptrace

**Documentation:** https://www.muflone.com/gptrace/

System Requirements
-------------------

* Python 3.x (developed and tested for Python 3.9.6)
* XDG library for Python 3
* GTK+ 3.0 libraries for Python 3
* GObject libraries for Python 3
* Distutils library for Python 3 (usually shipped with Python distribution)
* PTrace library for Python 3 (https://pypi.org/project/python-ptrace/)

Installation
------------

A distutils installation script is available to install from the sources.

To install in your system please use:

    cd /path/to/folder
    python setup.py install

To install the files in another path instead of the standard /usr prefix use:

    cd /path/to/folder
    python setup.py install --root NEW_PATH

Usage
-----

If the application is not installed please use:

    cd /path/to/folder
    python gptrace.py

If the application was installed simply use the gptrace command.
