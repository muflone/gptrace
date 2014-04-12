gpTrace
=======
**Description:** Trace the activities of an external application.

**Copyright:** 2014 Fabio Castelli (Muflone) <webreg(at)vbsimple.net>

**License:** GPL-2+

**Source code:** https://github.com/muflone/gptrace

**Documentation:** http://url.muflone.com/gptrace

System Requirements
-------------------

* Python 2.x (developed and tested for Python 2.7.5)
* XDG library for Python 2
* GTK+3.0 libraries for Python 2
* GObject libraries for Python 2
* Distutils library for Python 2 (usually shipped with Python distribution)

Installation
------------

A distutils installation script is available to install from the sources.

To install in your system please use:

    cd /path/to/folder
    python2 setup.py install

To install the files in another path instead of the standard /usr prefix use:

    cd /path/to/folder
    python2 setup.py install --root NEW_PATH

Usage
-----

If the application is not installed please use:

    cd /path/to/folder
    python2 gptrace.py

If the application was installed simply use the gptrace command.
