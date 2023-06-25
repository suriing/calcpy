#!/usr/bin/env python3
from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version('calcpy')
except PackageNotFoundError:
    __version__ = 'no-package'

CALCPY_PROFILE_NAME = 'calcpy'

import IPython
import IPython.lib.backgroundjobs
import traitlets
import sympy
import platform
import importlib
import json
import os
from contextlib import redirect_stdout

import calcpy.currency
import calcpy.formatters
import calcpy.transformers
import calcpy.info
import calcpy.autostore
import calcpy.preview

def get_calcpy():
    return IPython.get_ipython().calcpy

@IPython.core.magic.magics_class
class CalcPy(IPython.core.magic.Magics):
    debug = traitlets.Bool(False, config=True, help='Add debug prints')
    implicit_multiply = traitlets.Bool(True, config=True)
    auto_solve = traitlets.Bool(True, config=True)
    caret_power = traitlets.Bool(False, config=True)
    auto_lambda = traitlets.Bool(True, config=True)
    auto_store = traitlets.Bool(True, config=True)
    auto_matrix = traitlets.Bool(True, config=True)
    auto_date = traitlets.Bool(True, config=True)
    auto_symbols = traitlets.Bool(True, config=True)
    preview = traitlets.Bool(True, config=True)
    parse_latex = traitlets.Bool(True, config=True)
    bitwidth = traitlets.Int(0, config=True)
    chop = traitlets.Bool(True, config=True)
    eng_units_prefixes = traitlets.Bool(True, config=True)
    precision = property(
        lambda calcpy: calcpy.shell.run_line_magic('precision', ''),
        lambda calcpy, p: calcpy.shell.run_line_magic('precision', p))

    def __init__(self, shell=None, **kwargs):
        ''''''
        super(CalcPy, self).__init__(shell, **kwargs)

        self._eng_units_prefixes_dict = importlib.import_module('calcpy.eng_units_prefixes').__dict__

        self.user_startup_path = os.path.join(shell.profile_dir.location, 'user_startup.py')
        config_path = os.path.join(self.shell.profile_dir.location, 'calcpy.json')
        if os.path.isfile(config_path):
            try:
                with open(config_path, 'r') as f:
                    for trait_name, value in json.load(f).items():
                        setattr(self, trait_name, value)
            except Exception as e:
                print(f'Failed to read config from {config_path}: {repr(e)}')

        def calcpy_trait_observe(change):
            try:
                with open(config_path, 'w') as f:
                    json.dump(self.non_default_config_values(), f, indent=1)
            except Exception as e:
                print(f'Failed to write config from {config_path}: {repr(e)}')
        self.observe(calcpy_trait_observe)

        def _auto_store_changed(change):
            if change.old != change.new == True:
                calcpy.autostore.load_ipython_extension(self.shell)
            if change.old != change.new == False:
                calcpy.autostore.unload_ipython_extension(self.shell)
        self.observe(_auto_store_changed, names='auto_store')

        def _preview_changed(change):
            if change.old != change.new == True:
                calcpy.preview.load_ipython_extension(self.shell)
            if change.old != change.new == False:
                calcpy.preview.unload_ipython_extension(self.shell)
        self.observe(_preview_changed, names='preview')

        def _eng_units_prefixes_changed(change):
            if change.new == True:
                calcpy.push(self._eng_units_prefixes_dict, interactive=False)
            if change.new == False:
                for key in self._eng_units_prefixes_dict:
                    self.shell.user_ns.pop(key, None)
                    self.shell.user_ns_hidden.pop(key, None)
        self.observe(_eng_units_prefixes_changed, names='eng_units_prefixes')

        CalcPy.__doc__ = "CalcPy\n"
        for trait_name, trait in sorted(self.traits(config=True).items()):
            CalcPy.__doc__ += self.class_get_trait_help(trait, None).replace('--CalcPy.', '') + '\n'

    def non_default_config_values(self):
        non_def = {}
        trait_defaults = self.trait_defaults(config=True)
        for trait_name, value in self.trait_values(config=True).items():
            if value != trait_defaults[trait_name]:
                non_def[trait_name] = value
        return non_def

    def push(self, variables, interactive=True):
        self.shell.push(variables, interactive)
        try:
            self.shell.previewer.isolated_ns.update(variables)
        except AttributeError:
            pass

    def __repr__(self):
        config = self.trait_values(config=True)
        return 'CalcPy ' + repr(config)

    def edit_user_startup(self):
        self.shell.run_line_magic('edit', self.user_startup_path)

    def reset(self, prompt=True):
        if prompt:
            if input("Confirm reset? [y/N] ").lower() not in ["y","yes"]:
                return
        for trait_name, trait in sorted(self.traits(config=True).items()):
            setattr(self, trait_name, trait.default_value)
        self.shell.autostore.reset()

def load_ipython_extension(ip:IPython.InteractiveShell):
    if ip.profile != CALCPY_PROFILE_NAME:
        print(f'warning: Not using the {CALCPY_PROFILE_NAME} profile (current profile is {ip.profile}')

    ip.calcpy = CalcPy(ip)
    ip.push({'calcpy': ip.calcpy}, interactive=False)

    ip.register_magics(ip.calcpy)

    ip.calcpy.jobs = IPython.lib.backgroundjobs.BackgroundJobManager()

    def show_usage():
        print(f'''CalcPy {__version__} (Python {platform.python_version()} IPython {IPython.__version__} SymPy {sympy.__version__})
https://github.com/idanpa/calcpy''')

    ip.show_usage = show_usage

    ip.push(importlib.import_module('calcpy.user').__dict__, interactive=False)
    if ip.calcpy.eng_units_prefixes:
        ip.push(ip.calcpy._eng_units_prefixes_dict, interactive=False)

    try:
        with redirect_stdout(None): # some recent IPython version prints here
            ip.enable_pylab(import_all=False)
    except ImportError:
        pass # no gui

    calcpy.formatters.init(ip)
    calcpy.transformers.init(ip)
    calcpy.info.init(ip)
    calcpy.currency.init(ip)

    # we hide ourselves all initial variable, (instead of ipython InteractiveShellApp.hide_initial_ns)
    # so autostore and user startups variables would be exposed to who, who_ls
    ip.user_ns_hidden.update(ip.user_ns)

    if ip.calcpy.auto_store:
        calcpy.autostore.load_ipython_extension(ip)

    if os.path.isfile(ip.calcpy.user_startup_path):
        ip.user_ns['__file__'] = ip.calcpy.user_startup_path
        ip.safe_execfile(ip.calcpy.user_startup_path,
                         ip.user_ns,
                         raise_exceptions=False,
                         shell_futures=True)

    if ip.calcpy.preview and 'code_to_run' not in ip.config.InteractiveShellApp:
        calcpy.preview.load_ipython_extension(ip)

if __name__ == '__main__':
    load_ipython_extension(IPython.get_ipython())
