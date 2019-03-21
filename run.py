# -  *  - coding:utf-8  -  *  -
import time
import unittest

from multiprocessing import Manager
import os
from multiprocessing.pool import Pool

import xlrd

from common.httprequest import HttpRequest
from common.utils import get_excel

from common.data import Data
from config import globalparam


class Run():
    def __init__(self):
        self.unittest_runner = unittest.TextTestRunner()
        self.test_loader = unittest.TestLoader()

    def addTest(self, excle):

        def add_test(name, runner):

            def test(self):
                try:
                    runner.run()
                except Exception as e:
                    if isinstance(e, (TypeError, PermissionError)):
                        self.fail(e)
                    else:
                        raise e

            test.__doc__ = name

            return test

        test_suite = unittest.TestSuite()
        data = Data(excle)
        data.run()
        tests = data.suite
        config = tests.get("config", None)
        suite = tests.get("suite", None)
        step = tests.get("step", None)
        cases = tests.get("case", None)

        setattr(HttpRequest, "config", config)
        TestObject = type('TestObject', (unittest.TestCase,), {})

        for index, case in enumerate(cases):
            for k, v in case.items():
                httpRequest = HttpRequest(v, suite=suite, step=step)
                test_name = 'test_{}--->{}'.format(index, v)
                test_method = add_test(excle, httpRequest)
                setattr(TestObject, test_name, test_method)

        loaded_testcase = self.test_loader.loadTestsFromTestCase(TestObject)
        test_suite.addTest(loaded_testcase)

        return test_suite

    def add_result(self, suite):
        tests_results = []
        for tests in suite:
            result = self.unittest_runner.run(tests)
            tests_results.append(result)
        return tests_results

    def run(self):
        excles = get_excel()
        for excle in excles:
            test_suite = self.addTest(excle)
            self.add_result(test_suite)


if __name__ == "__main__":
    test = Run()
    test.run()
