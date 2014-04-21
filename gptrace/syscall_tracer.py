from ptrace.debugger import PtraceDebugger, Application, ProcessExit, ProcessSignal
from ptrace.func_call import FunctionCallOptions
from ptrace.syscall import SYSCALL_NAMES, SYSCALL_PROTOTYPES, FILENAME_ARGUMENTS, SOCKET_SYSCALL_NAMES
from ptrace.ctypes_tools import formatAddress

class SyscallTracer(Application):
  def __init__(self, options, program, ignore_syscall_callback, syscall_callback, event_callback):
    Application.__init__(self)
    # Parse self.options
    self.options = options
    self.program=[program, ]
    self.parseOptions()
    self.ignore_syscall_callback = ignore_syscall_callback
    self.syscall_callback = syscall_callback
    self.event_callback = event_callback

  def parseOptions(self):
    self.options.fork = False
    self.options.enter = False
    self.options.show_ip = False
    self.options.trace_exec = True
    #self.options.socket = False
    #self.options.filename = False
    self.options.pid = None
    self.options.no_stdout = False
    self.options.show_pid = False


    #if self.options.list_syscalls:
    #    syscalls = list(SYSCALL_NAMES.items())
    #    syscalls.sort(key=lambda data: data[0])
    #    for num, name in syscalls:
    #        print("% 3s: %s" % (num, name))
    #    exit(0)

    # Create "only" filter
    only = set()
    #if self.options.filename:
    #    for syscall, format in SYSCALL_PROTOTYPES.items():
    #        restype, arguments = format
    #        if any(argname in FILENAME_ARGUMENTS for argtype, argname in arguments):
    #            only.add(syscall)
    #if self.options.socket:
    #    only |= SOCKET_SYSCALL_NAMES
    self.only = only
    self.excluding = ('sendmsg', 'recvmsg', 'connect', 'socket', 'getsockopt', 'sendto', 'recvfrom', 'listen', 'getsockname', 'getpeername', 'poll', 'futex', 'write', 'writev', 'read', 'stat', 'fstat', 'close', 'open', 'shmctl', 'shmget', 'shmdt', 'fcntl', 'brk', 'mmap', 'munmap', 'mprotect', 'lseek', 'lstat', 'fstatfs', 'access', 'getdents', 'fadvise64', 'openat', 'getressgid', 'getresuid', 'getegid', 'getressgid', 'shmat', 'syscall<290>', 'geteuid', 'getuid', 'rt_sigaction', 'getresgid', 'clone', 'set_tid_address')
    self.excluding = ()

    if self.options.fork:
        self.options.show_pid = True
    self.processOptions()

  def runDebugger(self):
    # Create debugger and traced process
    self.setupDebugger()
    process = self.createProcess()
    if not process:
        return

    self.syscall_options = FunctionCallOptions(
        write_types=True,
        write_argname=True,
        string_max_length=300,
        replace_socketcall=False,
        write_address=True,
        max_array_count=20,
    )
    self.syscall_options.instr_pointer = self.options.show_ip
    self.syscallTrace(process)

  def displaySyscall(self, syscall):
    self.syscall_callback(syscall)
    #name = syscall.name
    #text = syscall.format()
    #if syscall.result is not None:
    #    text = "%-40s = %s" % (text, syscall.result_text)
    #prefix = []
    #if self.options.show_pid:
    #    prefix.append("[%s]" % syscall.process.pid)
    #if self.options.show_ip:
    #    prefix.append("[%s]" % formatAddress(syscall.instr_pointer))
    #if prefix:
    #    text = ''.join(prefix) + ' ' + text
    #error(text)

  def syscall(self, process):
    state = process.syscall_state
    syscall = state.event(self.syscall_options)
    if syscall and (syscall.result is not None or self.options.enter):
      self.displaySyscall(syscall)

    # Break at next syscall
    process.syscall()

  def syscallTrace(self, process):
    # First query to break at next syscall
    self.prepareProcess(process)

    while True:
      # No more process? Exit
      if not self.debugger:
        break

      # Wait until next syscall enter
      try:
        event = self.debugger.waitSyscall()
        process = event.process
      except ProcessExit as event:
        self.processExited(event)
        continue
      except ProcessSignal as event:
        self.event_callback(event)
        event.display()
        process.syscall(event.signum)
        continue
      except NewProcessEvent as event:
        self.event_callback(event)
      #  self.newProcess(event)
        continue
      except ProcessExecution as event:
        self.event_callback(event)
      #  self.processExecution(event)
        continue

      # Process syscall enter or exit
      self.syscall(process)

  def prepareProcess(self, process):
    process.syscall()
    process.syscall_state.ignore_callback = self.ignore_syscall_callback

  def processExited(self, event):
    # Display syscall which has not exited
    state = event.process.syscall_state
    if (state.next_event == "exit") \
    and (not self.options.enter) \
    and state.syscall:
        self.displaySyscall(state.syscall)
    self.event_callback(event)

  def main(self):
    self.debugger = PtraceDebugger()
    try:
      self.runDebugger()
    except ProcessExit as event:
      self.processExited(event)
    self.debugger.quit()
