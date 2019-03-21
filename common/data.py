# -  *  - coding:utf-8  -  *  -
import collections
import os
import sys
import re
import time
import xlrd

import json
from common.exception import ExcelError
from common.httprequest import HttpRequest
from common.log import Log
from config import globalparam

log = Log()
headers_regexp = r"\{(.*)\}"


class Data(object):

    def __init__(self, file):
        self.suites = []
        self.file = file
        self.initialization()

    def initialization(self):
        self.suite = {
            "name": "",
            "config": {
                "headers": {},
                "variables": {},
                "base_url": ""
            },
            "suite": [],
            "step": [],
            "case": []
        }

    def get_sheets(self):
        sheets = []
        excel = os.path.join(globalparam.test_path, self.file)
        workbook = xlrd.open_workbook(excel)
        sheets_list = workbook.sheets()
        for sheet in sheets_list:
            if sheet.ncols != 0 and sheet.ncols != 0:
                sheets.append(sheet)
        return sheets

    def __suite(self, sheet):
        cols = sheet.col_values(0)

        try:
            config_index = cols.index("config")
        except ValueError:
            config_index = None
            self.suite["config"] = {}
        try:
            suite_index = cols.index("suite")
        except ValueError:
            suite_index = None
        try:
            step_index = cols.index("step")
        except ValueError:
            step_index = None
        try:
            case_index = cols.index("id")
        except ValueError:
            case_index = None
        if suite_index:
            self.validate_suite(sheet, name="suite", index=suite_index)
        if step_index:
            self.validate_suite(sheet, name="step", index=step_index)
        if config_index:
            self.validate_suite(sheet, name="config", index=config_index)
        if case_index:
            self.validate_suite(sheet, name="case", index=case_index)

    def validate_suite(self, sheet, name=None, index=None):
        spacing = None
        cols = sheet.col_values(0)
        suite_list = []
        if name == "case":
            spacing = len(cols)
        else:
            index += 1
            for col in cols[index:]:
                if col:
                    spacing = cols.index(col)
                    break

        for i in range(index, spacing):
            rows = sheet.row_values(i)
            # TODO 数据类型的处理(int,datetime,bool)
            for r in range(len(rows)):
                if isinstance(rows[r], float):
                    decimal = str(rows[r]).split(".")[1]
                    if len(decimal) == 1 and decimal == "0":
                        rows[r] = str(int(rows[r]))

            if rows.count("") != len(rows):
                if name in ("suite", "step", "case"):
                    if "id" in rows:
                        id_index = rows.index("id")
                        suite_list = rows[id_index:]
                    else:
                        if not suite_list:
                            log.error("{}-->{}--->not found id".format(self.file, name))
                            raise ExcelError
                        suites = list(zip(suite_list, rows[id_index:]))
                        # TODO 验证id,name,headers....
                        suite_dict = {}
                        suite_index = 0
                        for case in suites:
                            if case != ("", ""):
                                suite_dict[case[0]] = case[1]
                            if "id" in case and case[1]:
                                key = case[1]
                                suite_index += 1
                                self.suite[name].append(
                                    {
                                        name + case[1]: [suite_dict] if name == "suite" else suite_dict
                                    }
                                )
                            elif "id" in case and not case[1] and name == "suite":
                                self.suite[name][suite_index - 1][name + key].append(suite_dict)
                else:
                    suite_list.append(rows)

        if name == "config":
            if len(suite_list) != 2:
                log.error("{}--->config error".format(self.file))
                raise ExcelError
            else:
                suites = list(zip(suite_list[0], suite_list[1]))
                for i in suites:
                    if i != ("", ""):
                        self.suite["config"][i[0]] = i[1]

    def config_scope(self):
        config = self.suite.get("config", None)
        cases = self.suite.get("case", None)
        _config = {}
        if config and cases:
            for k, v in config.items():
                if k != "variables":
                    _config[k] = v

            for case in cases:
                for key, value in case.items():
                    for k, v in value.items():
                        if k in _config:
                            if len(set(case)) != len(case):
                                log.error("{}:用例中行有重名-->{}".format(sys.argv[0], case))
                            else:
                                if k == "url":
                                    cases[cases.index(case)][key][k] += _config["base_rul"]
                                cases[cases.index(case)][key][k] = v or _config[k]
                        self.suite["case"] = cases

    def transform_type(self, suite=None):
        if suite == None:
            return {k: self.transform_type(v) for k, v in self.suite.items()}
        else:
            data = suite
        if isinstance(data, dict) and "headers" in data:
            for key, value in data.items():
                if key in ("variables", "extrack", "headers", "data", "json", "setup", "teardown") and value:
                    _variables = collections.OrderedDict()
                    value_josn = None
                    if key in ("headers", "data"):
                        if key == "data":
                            try:
                                value_josn = eval(value)
                            except Exception as e:
                                log.error("{} is error-->{}".format(key, value))
                                raise e
                            else:
                                if not isinstance(value_josn, dict):
                                    log.error("{} not dict-->".format(key, value_josn))
                                    raise TypeError
                        else:
                            ret = re.match(headers_regexp, value)
                            if not ret:
                                log.error("{} is error -->{}".format(key, value))
                                raise ExcelError
                            else:
                                value = ret.group(1)
                    if "," in value and ("[" not in value or "(" not in value or "{" not in value):
                        variable = value.split(",")
                        if key in ("setup", "teardown"):
                            data[key] = variable
                        else:
                            if not value_josn:
                                for var in variable:
                                    try:
                                        k, v = var.split(":", 1)
                                    except ValueError:
                                        log.error('{}-->{}缺少 ":"'.format(key, value))
                                        raise ExcelError
                                    _variables[k.strip()] = v.strip()
                                    data[key] = _variables
                            else:
                                # TODO dict
                                data[key] = value_josn
                    else:
                        if key in ("setup", "teardown"):
                            data[key] = [value]
                        else:
                            if not value_josn:
                                try:
                                    k, v = value.split(":", 1)
                                except ValueError:
                                    log.error('{}-->{}缺少 ":"'.format(key, value))
                                    raise ExcelError
                                _variables[k.strip()] = v.strip()
                                data[key] = _variables
                            else:
                                data[key] = value_josn
            return data

        elif isinstance(data, list):
            return [self.transform_type(i) for i in data]

        elif isinstance(data, dict) and "headers" not in data:
            return {k: self.transform_type(v) for k, v in data.items()}

        elif isinstance(data, str):
            return data

    def run(self):
        # 构建测试用例结构
        self.initialization()
        sheets = self.get_sheets()
        for sheet in sheets:
            setattr(HttpRequest, "name", sheet.name)
            self.suite["name"] = sheet.name
            self.__suite(sheet)
            self.config_scope()
            self.suite = self.transform_type()
            print(self.suite)
            self.suites.append(self.suite)


if __name__ == "__main__":
    star_time = time.time()
    data = Data("test.xlsx")
    data.run()
    # print(data.suites)
    print(time.time() - star_time)
