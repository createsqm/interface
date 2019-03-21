# -  *  - coding:utf-8  -  *  -
import ast
import types
from json import JSONDecodeError

from common.exception import HookError, FunctionError, VariableError, ValidateError
from common import api, utils

import types
import re
from common.log import Log

log = Log()

is_function_regexp = re.compile(r"\$(([\w_])+\(.*\))")
variable_regexp = re.compile(r"^\$(.*)")
function_regexp = re.compile(r"^\$(\w+)\((.*)\)$")
text_extractor_regexp_compile = re.compile(r".*\(.*\).*")


def get_modules_function():
    modules = {}
    for key, value in vars(api).items():
        if isinstance(value, types.FunctionType):
            func_name = value.__name__
            modules[func_name] = value
    return modules


def parse_string_value(str_value):
    try:
        return ast.literal_eval(str_value)
    except ValueError:
        return str_value
    except SyntaxError:
        return str_value


def is_function(content):
    matched = is_function_regexp.match(content)
    return True if matched else False


def is_variable(content):
    matched = variable_regexp.match(content)
    return True if matched and "(" not in matched.group() else False


def parse_function(content):
    matched = function_regexp.match(content)
    if not matched:
        log.error("{} not found".format(content))
        raise FunctionError
    function_meta = {
        "func_name": matched.group(1),
        "args": [],
        "kwargs": {}
    }
    args_str = matched.group(2)
    if not args_str:
        return function_meta

    args_list = args_str.split(',')
    for arg in args_list:
        arg = arg.strip()
        if '=' in arg:
            key, value = arg.split('=')
            function_meta["kwargs"][key.strip()] = parse_string_value(value.strip())
        else:
            function_meta["args"].append(parse_string_value(arg))

    return function_meta


def request_variables(req, variables):
    """
    :param request:
    "req": {
                        "url": "http://www.httpbin.org/post",
                        "method": post,
                        "headers": {},
                        "data": {"key":"$value"}
                    }
    :return:
    {
                        "url": "http://www.httpbin.org/post",
                        "method": post,
                        "headers": {},
                        "data": {"key":"value"}
                    }
    """

    def variable(data):

        if isinstance(data, dict):
            return {variable(key): variable(value) for key, value in data.items()}

        if isinstance(data, list):
            return [variable(i) for i in data]

        if isinstance(data, str):
            if is_variable(data):
                matched = variable_regexp.match(data)
                value = matched.group(1)
                if value not in data:
                    log.error("{} not found--->{}".format(value, variables))
                    raise VariableError
                return value

            elif is_function(data):

                log.error("{} function defined in case variables".format(data))

                raise ValidateError


            else:

                return data

        if isinstance(data, (int, float)):
            return data

        else:
            log.error("Invalid type--->expect:{}".format(data))
            raise TypeError

    request = variable(req)
    return request


def parse_variables(data):
    """
    :param variables:{
        "token": "$token",
        "get_str": "$str()",
        "test_func":"$test_func(1, 2, a=3, b=$get_str)"
    }

    :return:{
        "token": "xxxx,
        "get_str": "xx",
        "test_func":"yyy"
    }
    """
    if isinstance(data, dict):
        return {key: parse_variables(value) for key, value in data.items()}

    if isinstance(data, (tuple, list)):
        return [parse_variables(item) for item in data]

    if isinstance(data, (int, float)):
        return data

    data = "" if data is None else data.strip()

    if is_variable(data):
        return data

    elif is_function(data):
        data = parse_function(data)
        return data
    else:
        return data


def parse_eval_variables(data):
    map_variables = data

    def eval_variables(data, name=None):
        if isinstance(data, dict):
            value = {eval_variables(key): eval_variables(value, key) for key, value in data.items()}
            if name:
                map_variables[name] = value
            return value

        elif isinstance(data, (list, tuple)):
            value = [eval_variables(i) for i in data]
            if name:
                map_variables[name] = value
            return value

        elif isinstance(data, str):
            if is_variable(data):
                value = eval_variable(data, map_variables)
                if name:
                    map_variables[name] = value
                return value

            elif is_function(data):
                data = parse_variables(data)
                value = eval_function(data)
                if name:
                    map_variables[name] = value
                return value

            else:
                return data
        elif isinstance(data, (int, float)):
            return data
        else:
            log.error("invalid type--->{}".format(data))
            raise TypeError

    def eval_variable(var, data):
        matched = variable_regexp.match(var)
        value = matched.group(1)
        if value not in data:
            log.error("{} not found--->{}".format(value, data))
            raise VariableError
        return data[value]

    def eval_function(function):
        modules = get_modules_function()
        func_name = function.get("func_name")
        args = function.get("args")
        kwargs = function.get("kwargs")
        if func_name not in modules:
            log.error("function undefined--->{}".format(func_name))
            raise FunctionError
        else:
            func = modules[func_name]
            args_value = []
            kwargs_value = {}
            if args:
                for arg in args:
                    value = eval_variables(arg)
                    args_value.append(value)

            if kwargs:
                kwargs_value = {eval_variables(key): eval_variables(value) for key, value in kwargs.items()}
            result = eval("func(*args_value, **kwargs_value)")
            return result

    variables = eval_variables(data)
    return variables


def _extract_field_with_regex(field, res):
    machted = re.search(field, res.text)
    if not machted:
        log.error("Failed to extract data with regex-->{}\n response boby-->{}".format(field, res.text))
        raise ValidateError
    return machted.group(1)


def _extract_field_with_delimiter(field, res):
    top_query, sub_query = field.split('.', 1)
    response_attributes = {key.lower(): value for key, value in res.__dict__.items()}
    if not hasattr(res, top_query):
        log.error("response No such attribute--->{}".format(top_query))
        raise ValidateError
    if top_query == "cookies":
        cookies = res.cookies
        try:
            return cookies[sub_query]
        except KeyError:
            err_msg = "Failed to extract cookie! => {}\n".format(field)
            err_msg += "response cookies: {}\n".format(cookies)
            log.error(err_msg)
            raise ValidateError

    elif top_query == "elapsed":
        if sub_query in ["days", "seconds", "microseconds"]:
            return getattr(res.elapsed, sub_query)
        elif sub_query == "total_seconds":
            return res.elapsed.total_seconds()
        else:
            err_msg = "{} is not valid datetime.timedelta attribute.\n".format(sub_query)
            log.error(err_msg)
            raise ValidateError(err_msg)
    elif top_query == "headers":
        headers = res.headers
        try:
            return headers[sub_query]
        except KeyError:
            err_msg = "Failed to extract header! => {}\n".format(field)
            err_msg += "response headers: {}\n".format(headers)
            log.error(err_msg)
            raise ValidateError(err_msg)
    elif top_query in ["content", "text", "json"]:
        try:
            body = res.json
        except JSONDecodeError:
            body = res.text

        if isinstance(body, (dict, list)):
            return utils.query_json(body, sub_query)
        elif sub_query.isdigit():
            return utils.query_json(body, sub_query)

        elif top_query in response_attributes:
            attributes = response_attributes[top_query]
            if isinstance(attributes, (dict, list)):
                return utils.query_json(attributes, sub_query)
            elif sub_query.isdigit():
                return utils.query_json(attributes, sub_query)
            else:
                err_msg = "Failed to extract {} set attribute from response!".format(attributes)
                log.error(err_msg)
                raise ValidateError
        elif top_query in res.__dict__:
            attributes = res.__dict__[top_query]

            if not sub_query:
                return attributes

            if isinstance(attributes, (dict, list)):
                return utils.query_json(attributes, sub_query)
            elif sub_query.isdigit():
                return utils.query_json(attributes, sub_query)
            else:
                err_msg = "Failed to extract cumstom set attribute from teardown hooks! => {}\n".format(field)
                err_msg += "response set attributes: {}\n".format(attributes)
                log.error(err_msg)
                raise ValidateError

        else:
            err_msg = u"Failed to extract attribute from response! => {}\n".format(field)
            err_msg += u"available response attributes: status_code, cookies, elapsed, headers, content, text, json, encoding, ok, reason, url.\n\n"
            err_msg += u"If you want to set attribute in teardown_hooks, take the following example as reference:\n"
            err_msg += u"response.new_attribute = 'new_attribute_value'\n"
            log.error(err_msg)
            raise ValidateError


def _eval_check_item(validator, res, config):

    def eval_check_value(check_value):
        if is_variable(check_value):
            var = variable_regexp.match(check_value).group(1)
            if var not in config:
                log.error("{} variable undefined--->{}".format(check_value, config))
                raise ValidateError
            return config[var]

        elif is_function(check_value):
            log.error("{} function defined in case variables".format(check_value))
            raise ValidateError

        if hasattr(res, check_value):
            return res.check_value
        else:
            if text_extractor_regexp_compile.match(check_value):
                value = _extract_field_with_regex(check_value, res)
                return value
            else:
                value = _extract_field_with_delimiter(check_value, res)
                return value

    def eval_expect(expect):
        if isinstance(expect, list):
            return [eval_expect(i) for i in expect]

        if isinstance(expect, dict):
            return {eval_expect(key): eval_expect(value) for key, value in expect.items()}

        if isinstance(expect, str):
            if is_variable(check_value):
                var = variable_regexp.match(check_value).group(1)
                if var not in config:
                    log.error("{} variable undefined--->{}".format(check_value, config))
                    raise ValidateError
                return config[var]

            elif is_function(check_value):
                log.error("{} function defined in case variables".format(check_value))
                raise ValidateError
            else:
                return expect

        if isinstance(expect, (int, float)):
            return expect
        else:
            log.error("Invalid type--->expect:{}".format(expect))
            raise TypeError

    check_value = validator.get("check_value")
    expect = validator.get("expect")
    validator["check_value"] = eval_check_value(check_value)
    validator["expect"] = eval_expect(expect)
    return validator


def parse_eval_validate(validate, res, config):
    """
    :param validator:
    [{'check': 'eq',
     'check_value': 'status_code',
     'expect': 200
     },
     {'check': 'eq',
     'check_value': 'status_code',
     'expect': $expect_status_code
     },
     {'check': 'len_eq',
     'check_value': '$token',
     'expect': $token_len
     },
     {'check': '$custom_function',
     'check_value': '$token',
     'expect': $token_len
     },
     {'check': 'eq',
     'check_value': "AAA11(.*)BB456",
     'expect': "abc"
     }]
    :return:
    """
    validators = parse_validate(validate)

    if not validators:
        return []

    log.debug("start to validate")

    for validator in validators:
        evaluated_validator = _eval_check_item(
            validator,
            res,
            config
        )






def parse_validate(validate):
    """
    :param validator:
    validator = '"eq":["status_code",200],
    "eq': ["status_code", "$expect_status_code"],
    "len_eq": ["$token", "$token_len"],
    "len_status_code": ["status_code", 200],
    "len":["content.status_code":3],
    "eq": ["AAA11(.*)BB456", "abc"]'
    :return:
    [{'check': 'eq',
     'expect': 'status_code',
     'comparator': 200
     }.....]
    """
    # check = ["eq", "len_eq", "in", "len"]
    validator = []
    validates = validate.split("],")
    for index, value in enumerate(validates):
        if not index == len(validates) - 1:
            check_type = value.split(":")[0]
            check_type = parse_string_value(check_type)
            check_item = value.split(":")[1] + "]"
        else:
            check_type = str(value.split(":")[0])
            check_type = parse_string_value(check_type)
            check_item = value.split(":")[1]
        # if check_type not in check:
        #     log.error("{} not in {}".format(check_type, check))
        #     raise ValidateError
        matched = re.match(r"\[(.*?),(.*)\]", check_item)
        if not matched:
            log.error("Invalid validate--->{}".format(check_item))
            raise ValidateError
        else:
            validator.append(
                {
                    "check": check_type,
                    "check_value": parse_string_value(matched.group(1)),
                    "expect": parse_string_value(matched.group(2))
                }
            )
    return validator


if __name__ == "__main__":
    data = {
        "fun": "$get_string()",
        "random": "$fun",
        "get_random": {"$random": 111},
        "get_string": "$get_random_string($get_random, value=$fun)",
        "get": "$get_string",
        "$fun": "111"
    }

    date = parse_eval_variables(data)
    print(date)

    test = '"eq":["status_code",[200,201]],"eq":["AAA11(.*)BB456","abc"],"len":["content.status_code",3]'
    t = parse_validate(test)
    print(t)
