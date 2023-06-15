#!/usr/bin/env python3

import calcpy
import IPython
import argparse
import subprocess
import shutil
import os

import threading
import prompt_toolkit.patch_stdout
from functools import partial

# TODO: how to do this dynamically?
from prompt_toolkit.styles.defaults import PROMPT_TOOLKIT_STYLE
PROMPT_TOOLKIT_STYLE.remove((('bottom-toolbar', 'reverse')))
PROMPT_TOOLKIT_STYLE.append((('bottom-toolbar', 'noreverse')))

def start_ipython(args, conn):
    # os.sys.stdout = conn
    os.sys.__stdout__ = conn
    IPython.start_ipython(args)

class ConnStream():
    def __init__(self, conn):
        self.conn = conn
    def write(self, obj):
        self.conn.send(obj)
    def flush(self):
        pass

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--gui', action='store_true', help='Launch CalcPy GUI')
    parser.add_argument('--version', action='store_true', help='Print version and exit')
    parser.add_argument('--debug', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('-c', '--command', help="Execute given command and exit")
    args, args_reminder = parser.parse_known_args()

    if args.version:
        print(f"CalcPy {calcpy.__version__}")
        return 0

    ipython_args = [
        "--TerminalIPythonApp.display_banner=False",
        "--InteractiveShell.separate_in=",
        #--InteractiveShellApp.extra_extensions is only supported from 7.10
        "--InteractiveShellApp.exec_lines=%load_ext calcpy",
        "--InteractiveShellApp.hide_initial_ns=False", # we parially hide them
        # TODO: float_precision should be configurable (at startup)
        "--PlainTextFormatter.float_precision=%.6g",
        "--TerminalInteractiveShell.confirm_exit=False",
        "--TerminalInteractiveShell.term_title_format=CalcPy",
        f"--profile={calcpy.CALCPY_PROFILE_NAME}",
    ]

    if args.debug:
        ipython_args.append("--CalcPy.debug=True")
        ipython_args.append("--TerminalInteractiveShell.xmode=verbose")

    if args.command:
        ipython_args.append(f"--InteractiveShellApp.code_to_run={args.command}")

    ipython_args.extend(args_reminder)

    # monkey patch prompt_toolkit to avoid printin from background for preview
    # TODO: need a better fix
    stdoutproxy_write = prompt_toolkit.patch_stdout.StdoutProxy.write
    def skip_asyncio_thread_write(self, data):
        if not threading.currentThread().name.startswith('asyncio'):
            return stdoutproxy_write(self, data)
        return len(data)  # Pretend everything was written.
    prompt_toolkit.patch_stdout.StdoutProxy.write = skip_asyncio_thread_write

    if args.gui:
        # need jupyter_client==6.1.12
        jupyter_path = shutil.which('jupyter')
        if jupyter_path is None:
            raise Exception('Jupyter was not found')

        qtconsole_cmd = [
            jupyter_path,
            "qtconsole",
            "--JupyterQtConsoleApp.display_banner=False",
            "--JupyterConsoleApp.confirm_exit=False",
            "--JupyterQtConsoleApp.hide_menubar=True",
            "--JupyterWidget.input_sep=",
        ]
        ipython_args.insert(0, "kernel")
        import multiprocessing
        import re

        parent_conn, child_conn = multiprocessing.Pipe()
        ipython_proc = multiprocessing.Process(target=start_ipython, args=(ipython_args, ConnStream(child_conn)))
        try:
            ipython_proc.start()
            ipython_stdout = ''
            while not (match := re.search('(--existing.*)\n', ipython_stdout, re.MULTILINE)):
                if parent_conn.poll(0.1):
                    ipython_stdout += parent_conn.recv()
            qtconsole_cmd.append(match[1].replace(' ', '='))
            subprocess.run(qtconsole_cmd)
        finally:
            ipython_proc.terminate()
    else:
        IPython.start_ipython(ipython_args)

if __name__ == "__main__":
    main()
