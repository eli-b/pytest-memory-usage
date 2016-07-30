# -*- coding: utf-8 -*-


def test_help_message(testdir):
    result = testdir.runpytest(
        '--help',
    )
    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines([
        'memory-usage:',
        '*--memory-usage*Report memory usage',
    ])


def test_memory_usage_ini_setting(testdir):
    testdir.makeini("""
        [pytest]
        memory_usage = True
    """)

    testdir.makepyfile("""
        import pytest

        @pytest.fixture
        def report_memory_usage(request):
            return request.config.getini('memory_usage')

        def test_report_memory_usage(report_memory_usage):
            assert report_memory_usage == True
    """)

    result = testdir.runpytest('-v')
    # The test fails when we set memory_usage for the internal test
    # to True. runpytest() doesn't like the way I write to the terminal.

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines([
        '*::test_report_memory_usage PASSED*',
    ])

    # make sure that that we get a '0' exit code for the testsuite
    assert result.ret == 0
