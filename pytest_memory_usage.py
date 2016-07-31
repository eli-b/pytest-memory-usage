# -*- coding: utf-8 -*-

import pytest
import _pytest.config
import os
import sys
import psutil
import gc


def pytest_addoption(parser):
    group = parser.getgroup('memory-usage')
    group.addoption(
        '--memory-usage',
        action='store_true',
        default=False,
        help='Report memory usage'
    )

    parser.addini('memory_usage', 'Report memory usage', type='bool', default=False)


configuration = None
writer = None


def pytest_configure(config):
    global configuration
    configuration = config
    global writer
    writer = _pytest.config.create_terminal_writer(config, sys.stdout)


class MemoryState(object):
    def __init__(self):
        self.clear()

    def clear(self):
        self.before_setup = None
        self.before_call = None
        self.after_setup = None
        self.after_call = None
        self.process = None


_TWO_20 = float(2 ** 20)


def get_memory(process, include_children=True):
    """Inspired by the memory_profiler module's implementation"""
    try:
        mem = process.memory_info()[0] / _TWO_20
        if include_children:
            for p in process.children(recursive=True):
                mem += p.memory_info()[0] / _TWO_20
        return mem
    except psutil.AccessDenied:
        return None


def get_process():
    pid = os.getpid()
    return psutil.Process(pid)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_setup(item):
    if configuration.getoption('memory_usage') or configuration.getini('memory_usage'):
        state.clear()
        state.process = get_process()
        gc.disable()
        state.before_setup = get_memory(state.process)
        yield
        state.after_setup = get_memory(state.process)
        gc.enable()
    else:
        yield


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item):
    if configuration.getoption('memory_usage') or configuration.getini('memory_usage'):
        gc.disable()
        state.before_call = get_memory(state.process)
        yield
        state.after_call = get_memory(state.process)
        gc.enable()
    else:
        yield


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item):
    if configuration.getoption('memory_usage') or configuration.getini('memory_usage'):
        outcome = yield
        report = outcome.get_result()
        memory_usage = 0
        if (state.before_setup is not None and
                state.after_setup is not None):
            memory_usage += state.after_setup - state.before_setup
        if (state.before_call is not None and
                state.after_call is not None):
            memory_usage += state.after_call - state.before_call
            report.__dict__.update(dict(memory_usage=memory_usage))
    else:
        yield


@pytest.hookimpl(trylast=True)
def pytest_runtest_logreport(report):
    if configuration.getoption('memory_usage') or configuration.getini('memory_usage'):
        if report.when == 'call' and report.passed:
            if hasattr(report, 'memory_usage'):
                writer.write(' ({memory_usage:.0f}MB'.format(memory_usage=report.memory_usage))
                if report.memory_usage < 0:
                    writer.write(' - gc.collect() probably called explicitly')
                writer.write(')')
    return None


state = MemoryState()

