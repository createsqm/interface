# -  *  - coding:utf-8  -  *  -
import time

import requests

from common.exception import CaseError, HookError, MethodError
from common.log import Log
from common.utils import omit_long_data

from common.variable import request_variables, parse_eval_variables, parse_eval_validate
from config.globalparam import timeout
from unittest.case import SkipTest

log = Log()


class HttpRequest(object):
    def __init__(self, case, step=None, suite=None, config=None, name=""):
        self.config = config or getattr(self, "config", {})
        if not config:
            variables = self.config.get("variables", {})
            self.config["variables"] = parse_eval_variables(variables)
        self.case = case
        self.suite = suite
        self.step = step
        self.name = getattr(self, "name", "")
        self.config_data = {
            "name": self.name,
            "config": {
                'variables': self.config.get("variables", {})
            },
        } if self.config else {}

    def initialization(self):
        self.case_data = {
            "name": self.case.get("name"),
            "current_variables": self.case.get("variables", {}),
            "flag": self.case.get("flag", 0),
            "validate": self.case.get("validate", []),
            "setup": self.case.get("setup", []),
            "teardown": self.case.get("teardown", []),
            "data":
                {
                    "request": {
                        "url": self.case.get("url"),
                        "method": self.case.get("method"),
                        "headers": self.case.get("headers"),
                        "data": self.case.get("data", {}),
                        "type": self.case.get("type", None),
                        "stream": self.case.get("stream", False),
                        "verify": self.case.get("verify", True)
                    },
                    "response": {
                        "status_code": "N/A",
                        "headers": {},
                        "encoding": None,
                        "content_type": ""
                    }
                },
            "stat": {
                "content_size": "N/A",
                "response_time_ms": "N/A",
                "elapsed_ms": "N/A",
            }
        }
        self.do_skip()
        current_variables = self.case_data.get("current_variables")
        variables = self.config.get("variables", {})
        current_variables = parse_eval_variables(current_variables)
        variables.update(current_variables)
        self.current_variables = variables
        if self.case_data.get("setup"):
            self.do_hook(self.case_data["name"], self.case_data.get("setup"))

    def do_skip(self):
        flag = self.case_data.get("flag")
        if flag == "1":
            raise SkipTest

    def run_suite_step(self, config, name, suite_step):
        if name.startswith("step"):
            runner = HttpRequest(case=suite_step, config=config, name=name)
            runner.run()
        else:
            for suite in suite_step:
                runner = HttpRequest(case=suite, config=config, name=name)
                runner.run()
                config += runner.config
        return config

    def do_hook(self, name, hooks):
        config = self.current_variables
        for hook in hooks:
            if hook.startswith("step"):
                if not self.step:
                    log.error("{}-->step is empty".format(self.name))
                    raise HookError
                else:
                    step_name = [key for i in self.step for key in i.keys()]
                    if hook not in step_name:
                        log.error("{} not found---> {}".format(self.case_data.get("name"), hook))
                    else:
                        config = self.run_suite_step(config, hook, self.step[0])

            elif hook.startswith("suite"):
                if not self.step:
                    log.error("{}-->suite is empty".format(self.name))
                    raise HookError
                else:
                    step_name = [key for i in self.suite for key in i.keys()]
                    if hook not in step_name:
                        log.error("{} not found--->{}".format(self.case_data.get("name"), hook))
                    else:
                        config = self.run_suite_step(config, hook, self.suite)

            elif hook.startswith("mysql"):
                pass
            else:
                log.error("{}  hook not  'step' or 'suite' or 'mysql'-->{}".format(name, hooks))
                raise HookError

    def __del__(self):
        # teardown = self.case_data.get("teardown", None)
        # if teardown:
        #     self.do_hook(self.case_data.get("name"), teardown)
        pass

    def request(self):
        req = self.case_data["data"]["request"]
        req = request_variables(req, self.current_variables)
        url = req.get("url")
        method = req.get("method").upper()
        data = req.get("data")
        setup = self.case_data.get("setup")
        verify = req["verify"]
        req_type = req.get("type")
        if setup:
            self.do_hook(self.case_data["name"], setup)

        if method not in ["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]:
            log.error("Invalid HTTP method--->{}:{}".format(self.case_data.get("name"), method))
            raise MethodError
        else:
            start_time = time.time()
            if req_type and req_type != "json":
                log.error("type is not equal to 'json'--->{}".format(req_type))
                raise TypeError

            if req_type:
                try:
                    response = requests.request(method=method, url=url, json=data, timeout=int(timeout), verify=verify)
                    self.response_time_ms = round((time.time() - start_time) * 1000, 2)
                except TimeoutError:
                    log.error("HTTP request timeout ---->{}".format(self.case_data.get("name")))
                    raise
                except Exception as e:
                    log.error(str(e))
                    raise
            else:
                try:
                    response = requests.request(method=method, url=url, data=data, timeout=int(timeout), verify=verify)
                    self.response_time_ms = round((time.time() - start_time) * 1000, 2)
                except TimeoutError:
                    log.error("HTTP request timeout ---->{}".format(method))
                    raise
                except Exception as e:
                    log.error(str(e) + "--->{}".format(url))
                    raise
        return response

    def response(self, response):
        status_code = response.status_code
        res_headers = dict(response.headers)
        res_headers = {key.lower(): value for key, value in res_headers.items()}
        content_type = res_headers.get("content-type")
        self.case_data["data"]["response"]["headers"] = res_headers
        self.case_data["data"]["response"]["encoding"] = response.encoding
        self.case_data["data"]["response"]["content_type"] = content_type
        self.case_data["data"]["response"]["status_code"] = status_code
        self.case_data["data"]["response"]["url"] = response.url
        self.case_data["data"]["response"]["cookies"] = response.cookies
        self.case_data["data"]["response"]["reason"] = response.reason
        if "image" in content_type:
            # response is image type, record bytes content only
            self.case_data["data"]["response"]["content"] = response.content
        else:
            try:
                # try to record json data
                self.case_data["data"]["response"]["json"] = response.json()
            except ValueError:
                # only record at most 512 text charactors
                resp_text = response.text
                self.case_data["data"]["response"]["text"] = omit_long_data(resp_text)

        stream = self.case_data["data"].get("stream")

        if stream:
            content_size = int(dict(response.headers).get("content-length") or 0)
        else:
            content_size = len(response.content or "")

        # record the consumed time
        self.case_data["stat"] = {
            "response_time_ms": self.response_time_ms,
            "elapsed_ms": response.elapsed.microseconds / 1000.0,
            "content_size": content_size
        }

    def validate(self, response):
        validator = self.case_data.get("validate")
        validate = parse_eval_validate(validator, response, self.current_variables)


    def run(self):
        self.initialization()
        response = self.request()
        self.response(response)
        self.validate(response)
        print(self.case_data["data"]["request"])
        print(self.case_data["data"]["response"])
