# gpTrace

[![Travis CI Build Status](https://img.shields.io/travis/com/muflone/gptrace/master.svg)](https://www.travis-ci.com/github/muflone/gptrace)
[![CircleCI Build Status](https://img.shields.io/circleci/project/github/muflone/gptrace/master.svg)](https://circleci.com/gh/muflone/gptrace)

**Description:** Trace the activities of an external application

**Copyright:** 2014-2022 Fabio Castelli (Muflone) <muflone(at)muflone.com>

**License:** GPL-3+

**Source code:** https://github.com/muflone/gptrace

**Documentation:** https://www.muflone.com/gptrace/

**Translations:** https://explore.transifex.com/muflone/gptrace/

# Description

**gpTrace** can be used as an application debugger to discover what activities
an application does, which files accesses (or tries to use in the case they
miss), how many external processes are called and what arguments those processes
were using.

From the **gpTrace** main window you choose an executable file, click the button
**Start** and let the external program execute.

![Activities tab](https://www.muflone.com/resources/gptrace/archive/latest/english/main.png)

In the **Activities** tab you'll see the system calls were made and you can
filter what to see or what you prefer to ignore to better undestand what the
external program is doing.

![Counts tab](https://www.muflone.com/resources/gptrace/archive/latest/english/counts.png)

In the **Counts** tab you'll see how many calls are made for each system call.

![Files tab](https://www.muflone.com/resources/gptrace/archive/latest/english/files.png)

In the **Files** tab you'll the files the external program used or tried to use.
If you want to see only the existing files and ignore what files the process has
not found you can configure in the upper righe options menu.

![Files tab](https://www.muflone.com/resources/gptrace/archive/latest/english/main.png)

In the **Processes** tab you'll the external processes were called from your
application, along with their information and command line arguments.

![Options menu](https://www.muflone.com/resources/gptrace/archive/latest/english/options.png)

From the upper right button you can configure the program options. Some options
are also available clicking the mouse right button on the results list.

# Reliability

gpTrace uses a Python library called *ptrace* which, at the actual stage,
results unstable and sometimes unreliable, therefore you are warned the called
external program can fail, break, stop, hung or result unbearably slow.

In particular the opening and the closing processes are very delicate and
sometimes a crash could happen when you start an application or when you close a
running application.

If gpTrace hangs please kill the application using a process manager or the
terminal command *kill*.

# System Requirements

* Python >= 3.6 (developed and tested for Python 3.9 and 3.10)
* XDG library for Python 3 ( https://pypi.org/project/pyxdg/ )
* GTK+ 3.0 libraries for Python 3
* GObject libraries for Python 3 ( https://pypi.org/project/PyGObject/ )
* PTrace library for Python 3 ( https://pypi.org/project/python-ptrace/ )

# Installation

A distutils installation script is available to install from the sources.

To install in your system please use:

    cd /path/to/folder
    python setup.py install

To install the files in another path instead of the standard /usr prefix use:

    cd /path/to/folder
    python setup.py install --root NEW_PATH

# Usage

If the application is not installed please use:

    cd /path/to/folder
    python gptrace.py

If the application was installed simply use the gptrace command.
