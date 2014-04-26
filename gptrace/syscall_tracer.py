from ptrace.debugger import PtraceDebugger, Application, ProcessExit, ProcessSignal, NewProcessEvent, ProcessExecution
from ptrace.func_call import FunctionCallOptions
from ptrace.syscall import SYSCALL_NAMES, SYSCALL_PROTOTYPES, FILENAME_ARGUMENTS, SOCKET_SYSCALL_NAMES

class SyscallTracer(Application):
  def __init__(self, options, program, ignore_syscall_callback, syscall_callback, event_callback):
    Application.__init__(self)
    # Parse self.options
    self.options = options
    self.program=[program, ]
    self.processOptions()
    self.ignore_syscall_callback = ignore_syscall_callback
    self.syscall_callback = syscall_callback
    self.event_callback = event_callback

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
        #event.display()
        process.syscall(event.signum)
        continue
      except NewProcessEvent as event:
        self.event_callback(event)
        process = event.process
        self.prepareProcess(process)
        process.parent.syscall()
        continue
      except ProcessExecution as event:
        self.event_callback(event)
        process = event.process
        process.syscall()
        continue

      # Process syscall enter or exit
      self.syscall(process)

  def prepareProcess(self, process):
    process.syscall()
    process.syscall_state.ignore_callback = self.ignore_syscall_callback

  def processExited(self, event):
    # Display syscall which has not exited
    state = event.process.syscall_state
    if (state.next_event == "exit") and (not self.options.enter) and state.syscall:
      self.displaySyscall(state.syscall)
    self.event_callback(event)

  def main(self):
    self.debugger = PtraceDebugger()
    try:
      self.runDebugger()
    except ProcessExit as event:
      self.processExited(event)
    self.debugger.quit()
