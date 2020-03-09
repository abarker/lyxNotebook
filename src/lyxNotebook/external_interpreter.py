# -*- coding: utf-8 -*-
"""
=========================================================================
This file is part of LyX Notebook, which works with LyX but is an
independent project.  License details (MIT) can be found in the file
COPYING.

Copyright (c) 2012 Allen Barker
=========================================================================

This module provides the class `ExternalInterpreter`, which runs an external
interpreter and passes strings back and forth to it.  It uses a pseudo-tty to
run the specified interpreter interactively.  It works similarly to the Pexpect
program (that program might replace some parts at some point, but it works as
is).

Some of this code is based on an example from
http://stackoverflow.com/questions/4022600/python-pty-fork-how-does-it-work

Note that the Python interpreter's output can be redirected to a file, as::
   python >outfile
which only echos the input but sends all output to the file.

Redirecting stderr, output 2, sends the Python prompts to a different file::
   python >outfile 2>startupMessageAndPrompts

Maybe modify later to use a separate file, to avoid problems if a program
writes a prompt to output.

With scala::
   scala >outfile
*everything* goes into outfile, including echo of typed stuff.

"""

from __future__ import print_function, division
import sys
import os
import time
import pty
import signal
# import subprocess # for alternative where subprocess.call is used
from . import process_interpreter_specs # only needed for testing code at end


class ExternalInterpreter(object):
    """This class runs a single external interpreter.  There can be multiple
    instances, each running a possibly different interpreter application.  The
    interpreter is forked as a process connected to a pseudo-tty, so
    applications which expect terminal input can be run.  The only
    initialization argument is an interpreterSpec dict object which has the
    predefined collection of keys all defined."""

    def __init__(self, interpreter_spec):
        self.debug = False # debug flag, for verbose output
        # copy some of interpreter_spec data which is used in this
        # module to class member variables
        self.prog_name = interpreter_spec["prog_name"]
        self.inset_specifier = interpreter_spec["inset_specifier"]
        self.main_prompt = interpreter_spec["main_prompt"]
        self.cont_prompt = interpreter_spec["cont_prompt"]
        self.run_command = interpreter_spec["run_command"]
        self.run_arguments = interpreter_spec["run_arguments"]
        self.startup_sleep_secs = interpreter_spec["startup_sleep_secs"]
        self.before_read_sleep_secs = interpreter_spec["before_read_sleep_secs"]
        self.exit_command = interpreter_spec["exit_command"]

        self.running = False
        self.before_first_read = True
        self.before_first_read_or_write = True
        self.read_error_found = False
        if self.debug: print("running", self.prog_name)

        # try a pseudo-terminal fork
        try:
            # self.child_pid     is the child's PID
            # self.fd            is a Unix file number (not a Python handle) for pty
            # Note that fd acts as both stdin and stdout for the child process.
            self.child_pid, self.fd = pty.fork()
            # child_pid, fd = os.forkpty()    # OK (from original example, not tested)
        except OSError as e:
            print(str(e))

        # Note: unlike OS fork; in pty fork we MUST use the fd variable
        # somewhere (i.e. in parent process; it does not exist for child)
        # ... actually, we must READ from fd in parent process...
        # if we don't - child process will never be spawned!

        #
        # Child process handling code.
        #
        if self.child_pid == 0: # in child process
            # Warning: Errors generated by the child are not sent to the
            # usual stderr, and so it can appear to silently fail!
            # All print statements to stdout in child go to the pseudo-tty fd.

            # Note that child's fd is invalid (equal to -1); cannot write to it.
            if self.debug: print("   Child after pty.fork, fd is", self.fd,
                                 "and child_pid is", self.child_pid)

            # Note that child's print to stdout goes to the self.fd pseudo-tty file.
            # The write/print line below is necessary: it provides something for the
            # parent process to read to cause the child to be spawned.
            #print "In Child Process: PID# %s" % os.getpid()
            #print "In Child Process: PID=" + str(os.getpid())
            sys.stdout.write("   In Child Process: PID=" + str(os.getpid()) + "\n")
            sys.stdout.flush()

            # Run os.execlp to replace the child process with the program to run.
            # The arguments to os.execlp are:
            #    first, the executable of the command to be run (in the OS)
            #    second, a name of the executable for the process list ("ps axf")
            #    third and successive arguments are passed to the command as arguments
            # Example:
            #    os.execlp("python","ThePythonProgram", "-u", "pyecho.py")
            try:
                os.execlp(self.run_command, "LyxNotebook"+self.inset_specifier+"Process",
                          *self.run_arguments)
                # below line also works in place of above (with exit below and import)
                #subprocess.call([self.run_command]+self.run_arguments, shell=True)
            except:
                print("Cannot spawn execlp...")
            # sys.exit(0) # needed when subprocess.call is used above
        #
        # Parent process handling code.
        #
        else: # in parent process
            if self.debug: print("Parent after pty.fork, fd is", self.fd,
                                 "and child_pid is", self.child_pid)
            # This print below is not strictly necessary, but matches the one in child.
            if self.debug: print("In Parent Process: PID=" + str(os.getpid()))
            # We MUST read from fd in order for the child to be spawned.
            try:
                first_read_from_fd = os.read(self.fd, 10000)
            except OSError:
                self.report_read_error()
                return
            if self.debug: print(first_read_from_fd)
            # This ^^ line above prints out the "In Child Process..." string written
            # by the child process.
            self.spawn_time = time.time()

            # self.read_interpreter_init_message() # wait and do this on-demand (read/write)
        return

    def read_interpreter_init_message(self):
        """Read the initialization message from the interpreter, and the first
        prompt (after waiting at least self.startup_sleep_secs since self.spawn_time).
        This is an internal initialization routine."""
        time.sleep(max([0, (self.spawn_time + self.startup_sleep_secs) - time.time()]))
        #self.interpreterList[i].write("x=5\n")
        #self.interpreterList[i].write("print x*x\n")
        print("----- initialization message of interpreter", self.prog_name)
        print(self.read())
        print("----- end initialization of interpreter", self.prog_name)

    def write(self, string):
        """Writes to the stdin of the child's process.  The input string should be
        code that is executable in the interpreter, and should be newline terminated."""
        if self.before_first_read_or_write:
            # time.sleep(self.startup_sleep_secs)
            self.before_first_read_or_write = False
            self.read_interpreter_init_message()
        # write string to fd, returns # bytes
        string_byte_array = string.encode("utf-8") # encode for Python3 compatibility
        num_bytes_written = os.write(self.fd, string_byte_array) # return val currently unused
        sys.stdout.flush()
        # Before the first self.read we must read back the writes, or they will
        # produce a double echo effect... just how it works.  We don't need this
        # when readInterpreterInitMessage() always reads before a write, but it is
        # good to handle in general.
        if self.before_first_read and not self.read_error_found:
            # sys.stdout.flush()
            try:
                os.read(self.fd, 100000)
            except OSError:
                self.report_read_error()

    def read(self, max_bytes=100000, remove_backslash_r=True):
        """Reads from the stdout of the child process, up until a new prompt appears.
        The process is read until a prompt on a new line is detected.
        The directly read strings have newlines of \\r\\n, but by default the \\r
        values are removed before returning the final string value (since it can
        cause problems in later processing)."""
        if self.before_first_read_or_write:
            # time.sleep(self.startup_sleep_secs)
            self.before_first_read_or_write = False
            self.read_interpreter_init_message()
        read_string = ""
        while True:
            # brief sleep to make sure child has time to read any writes into its stdin
            time.sleep(self.before_read_sleep_secs)
            sys.stdout.flush()
            sys.stdin.flush() # probably not be needed
            # read at most max_bytes bytes from fd, return "" at EOF
            try:
                read_string += os.read(self.fd, max_bytes).decode(
                    "utf-8") # decode for Python3
            except OSError:
                self.report_read_error()
            if self.read_error_found:
                # return nothing for now, user must see message on screen
                self.report_read_error() # print message again
                err_string = u"\nError in LyxNotebook reading interpreter, see error" \
                    " messages.\n"
                err_string += self.main_prompt # add prompt so string appears in output
                return err_string

            # We read until the interpreter returns a prompt, so we know that it is
            # finished with its evaluation.

            # TODO: This can cause an error if
            # the code prints a newline followed by a prompt and then goes into
            # a calculation causing it to hang for a while.  Not likely, but worth
            # noting and considering.  If so, could reset prompt to an even less
            # likely string, or for some interpreters could redirect the prompt
            # strings to a named pipe to read from.  Or just "don't do that."
            #
            # Note this Python test case fails as expected.
            # def hang():
            #    print "\n>>> "
            #    time.sleep(4)
            #    print "not printed"
            # hang()

            lines = read_string.splitlines()  # keepends = False
            possible_main_prompt = lines[-1]
            possible_cont_prompt = lines[-1]

            # see if we really got a prompt...
            # note that some interpreters will add autoindent spaces, so look for prefix
            if (possible_main_prompt.find(self.main_prompt) == 0
                             and possible_main_prompt.rstrip() == self.main_prompt.rstrip()):
                if self.debug: print("got a main prompt, breaking")
                break
            if (possible_cont_prompt.find(self.cont_prompt) == 0
                             and possible_cont_prompt.rstrip() == self.cont_prompt.rstrip()):
                if self.debug: print("got a continuation prompt, breaking")
                break
            # This sleep only executes waiting for slow operations on the child to
            # return a prompt, or when there is some problem causing a hang
            time.sleep(0.5) # could sum up to get a maxTime for possible hangs, throw err
        if remove_backslash_r:
            # assume no naturally occurring \r characters and only " \r" or "\r\n"
            read_string = read_string.replace("\r\n", "\n")
            # very long lines sent to intrpreter can have " \r" inserted in result...
            read_string = read_string.replace(" \r", "")
            # now delete any remaining \r characters
            read_string = read_string.replace("\r", "")
        self.before_first_read = False
        return read_string

    def kill(self, soft=True, hard=False):
        """Do a soft or a hard kill, or both to try soft before hard."""
        # controlD = "\x04"
        if soft:
            exit_sequence = self.exit_command.splitlines(True) # keepends=True
            for command in exit_sequence:
                self.write(command)
            if hard: time.sleep(1) # wait one second for soft kill before trying hard
        if hard:
            os.kill(self.child_pid, signal.SIGKILL)
        os.waitpid(self.child_pid, 0)
        os.close(self.fd)
        self.running = False
        return

    def __del__(self):
        if self.running:
            self.kill(True, True)
        return

    def report_read_error(self):
        self.read_error_found = True
        print("Error in LyxNotebook reading the output from interpreter"
              "\nstarted with this command string:\n   ", self.run_command,
              "\nNo output can be read.  Are you sure the path to the"
              "\ninterpreter's executable is correct?", file=sys.stderr)
        return

#
# ====================== module tests =========================================
#

if __name__ == "__main__":

    print("--------------- starting tests of external_interpreter ONLY -----")
    interp = ExternalInterpreter(process_interpreter_specs.python)
    #interp = ExternalInterpreter(process_interpreter_specs.sage)
    print("created new external class")

    interp.write("x=5\n")
    interp.write("print x*x\n")
    print(interp.read())

    #sys.exit(0)

    in_chars = ""
    interp.write("x=5\n")
    in_chars += interp.read()
    #sys.stdout.write(in_chars); in_chars=""
    # Note extra \n required in line below, since raw writes are being used (not
    # the fancy version that sends newline on indentation down to zero) and we
    # will get a continuation prompt if only a single \n is sent.
    interp.write("if 4!=3: pass\n\n")
    in_chars += interp.read()
    sys.stdout.write(in_chars); in_chars = ""

    interp.write("print 'extra bonus 1'\n")
    # in_chars += interp.read()
    interp.write("print 'extra bonus 2'\n")
    #in_chars += interp.read()
    interp.write("print 'extra bonus 3'\n")
    in_chars += interp.read()
    sys.stdout.write(in_chars); in_chars = ""
    #print()
    #print("done first batch")

    interp.write("for i in range(0,10000): w=i+1\n\n") # note extra \n required!
    in_chars += interp.read() # if we read right after, avoid the piling-up double echo
    """
   If our controller process goes on and writes later lines while python churns
   on loop we can get the "piling up" effect, where stdin doesn't get read soon
   enough by the child process and so the parent reads it back, causing double echo
   (caused by child sharing stdin and stdout on a single file descriptor fd).
   This suggests that we should do a read after *each* line, really line by line
   We don't want the writer to get ahead of the child's stdin reader.
   """
    interp.write("print 'extra bonus 4'\n")
    interp.write("x=5\n")
    interp.write("x\n")
    interp.write("print 'extra bonus 5'\n")
    in_chars += interp.read()
    sys.stdout.write(in_chars); in_chars = ""
    #print()
    #print("done second batch")
    print("before soft kill")
    # interp.kill(soft=True, hard=True)
    print("after soft kill")
    interp.write("print 'this will be an error if kill above is uncommented'\n")
    print(interp.read())