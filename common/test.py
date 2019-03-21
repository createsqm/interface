# -  *  - coding:utf-8  -  *  -
import ast
import random
import re
import types
from _ast import Expression

import xlrd
import json
import collections
import requests
import unittest
# from common.data import get_excel
from common.exception import ExcelError
from common.log import Log
import os
from config import globalparam

log = Log()


def get_excel():
    # 获取所有xlsx,判断结构是否正确
    root = [root for root, dirs, files in os.walk(globalparam.test_path)]
    files = [files for root, dirs, files in os.walk(globalparam.test_path)]
    try:
        if len(files) > 1:
            raise ExcelError()
    except ExcelError:
        log.error("{}只允许有excel的测试用例-->{}".format(globalparam.test_path, root))
        return

    try:
        if len(files) == 1:
            files = files[0]
            for file in files:
                if not file.endswith(".xlsx") and file != "__init__.py":
                    raise ExcelError(file)
    except ExcelError:
        log.error("{}只允许有excel的测试用例-->{}".format(globalparam.test_path, file))
        return
    finally:
        files.remove("__init__.py")
        return files


# files = get_excel()
# for file in files:
#     if not file.endswith(".py"):
#         excel = os.path.join(globalparam.test_path, file)
#         workbook = xlrd.open_workbook(excel)
#         sheet_names = workbook.sheet_names()
#         sheet = workbook.sheet_by_name("Sheet1")
#         if sheet.ncols == 0 and sheet.nrows == 0:
#             sheet_names.remove(sheet.name)
#         col1 = sheet.col_values(0)
#         row = sheet.row_values(16)[3]


# for file in files:
#     excel = os.path.join(globalparam.test_path, file)
#     workbook = xlrd.open_workbook(excel)
#     sheets = workbook.sheets()
#     for sheet in sheets:
#         print(sheet.name)



# url = "http://httpbin.org/get"
# data = {"key": "value"}
# s = requests.request(method="GET", url=url, data=data)
# # print({key.lower(): value for key, value in s.__dict__.items()})
# for key, value in s.__dict__.items():
#     print(key, ":", value)

# import HTMLTestRunner
from unittest.case import SkipTest
from common.data import Data


class Test(object):
    def run_case(self, cases):
        self.config = getattr(self, "config", {})
        self.config["key"] += 1
        print(self.config)
        for name, value in cases.items():
            if name == "validata" and value == "status_code eq 200":
                raise ValueError


test_loader = unittest.TestLoader()
unittest_runner = unittest.TextTestRunner()


def addTest():
    def add_test(name, case, runner):
        def test(self):
            try:
                runner.run_case(case)
            except Exception as e:
                if isinstance(e, (TypeError, PermissionError)):
                    self.fail(e)
                else:
                    raise e

        test.__doc__ = name

        return test

    test_suite = unittest.TestSuite()
    data = Data("新建aXLSXa工作表.xlsx")
    testcases = {'case': [{'case1': {'id': '', 'name': '', 'method': '', 'headers': '', 'data': '',
                                     'validata': 'status_code eq 200', 'setup': '', 'teardown': ''}}, {
                              'case': {'id': '', 'name': 'normnal', 'method': 'post', 'headers': 'xxxx', 'data': '{}',
                                       'validata': '', 'setup': '', 'teardown': ''}}, {
                              'case': {'id': '', 'name': 'err_username', 'method': 'post', 'headers': 'xxxx',
                                       'data': '', 'validata': 'code eq 2', 'setup': '', 'teardown': ''}}, {
                              'case': {'id': '', 'name': '', 'method': '', 'headers': 'yyyy', 'data': '',
                                       'validata': '', 'setup': '', 'teardown': ''}}]}

    cases = testcases.get("case")
    test = Test()
    TestObject = type('TestObject', (unittest.TestCase,), {})
    for index, case in enumerate(cases):
        for k, v in case.items():
            test_name = 'test_{}--->{}'.format(k, v)
            test_method = add_test(k, v, test)
            setattr(TestObject, test_name, test_method)
            setattr(test, "config", {"key": 0})

    loaded_testcase = test_loader.loadTestsFromTestCase(TestObject)
    # setattr(loaded_testcase, "runtest", data)
    setattr(loaded_testcase, "runner", test)
    test_suite.addTest(loaded_testcase)

    return test_suite


def add_result(suite):
    tests_results = []
    for tests in suite:
        result = unittest_runner.run(tests)
        tests_results.append(result)
    return tests_results


# suite = addTest()
# results = add_result(suite)
# print(results)

meta_data = {
    "name": "",
    "data": [
        {
            "request": {
                "url": "N/A",
                "method": "N/A",
                "headers": {}
            },
            "response": {
                "status_code": "N/A",
                "headers": {},
                "encoding": None,
                "content_type": ""
            }
        }
    ],
    "stat": {
        "content_size": "N/A",
        "response_time_ms": "N/A",
        "elapsed_ms": "N/A",
    }
}


# test = '"eq":["status_code",[200,201]],"eq":["AAA11(.*)BB456","abc"],"len":["content.status_code",3]'
# print(test.split("],"))
# test = "AAA(11B)BB(45)6"
# text_extractor_regexp_compile = re.compile(r".*\(.*\).*")
# if text_extractor_regexp_compile.match(test):
#     print(11)
# else:
#     print(22)


# class Items():
#     def __init__(self, config=None):
#         self.config = config or getattr(self, "config", {})
#         print(self.config)
#
#     def run(self):
#         Items(config=123)
#
#
# for j in range(3):
#     setattr(Items, "config", random.randint(1, 10))
#     for i in range(3):
#         test = Items()
#     # test.run()