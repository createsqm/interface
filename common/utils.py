# -  *  - coding:utf-8  -  *  -
import os

from common import exception
from common.exception import ExcelError
from common.log import Log
from config import globalparam

log = Log()


def get_excel():
    # 获取所有xlsx,判断结构是否正确
    root = [root for root, dirs, files in os.walk(globalparam.test_path)]
    files = [files for root, dirs, files in os.walk(globalparam.test_path)]
    if len(files) > 1:
        log.error("{}must be 'xlsx' or 'xml'--->{}".format(globalparam.test_path, root))
        raise ExcelError

    if len(files) == 1:
        files = files[0]
        for file in files:
            if not file.endswith(".xlsx") and file != "__init__.py":
                log.error("{}must be 'xlsx' or 'xml'--->{}".format(globalparam.test_path, file))
                raise ExcelError
    files.remove("__init__.py")
    return files


def query_json(json_content, query):
    raise_flag = False
    response_body = u"response body: {}\n".format(json_content)
    try:
        for key in query.split("."):
            if isinstance(json_content, (list, str, bytes)):
                json_content = json_content[int(key)]
            elif isinstance(json_content, dict):
                json_content = json_content[key]
            else:
                log.error(
                    "invalid type value: {}({})".format(json_content, type(json_content)))
                raise_flag = True
    except (KeyError, ValueError, IndexError):
        raise_flag = True

    if raise_flag:
        err_msg = u"Failed to extract! => {}\n".format(query)
        err_msg += response_body
        log.error(err_msg)
        raise exception.ValidateError
    return json_content


def omit_long_data(body, omit_len=512):
    if not isinstance(body, (str, bytes)):
        return body

    body_len = len(body)
    if body_len <= omit_len:
        return body