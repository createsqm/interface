# -  *  - coding:utf-8  -  *  -
import os

from common.readconfig import ReadConfig

pro_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "config.ini")
read_config = ReadConfig(pro_path)
project_path = read_config.getValue("Project", "project_path")

# log日志路径
log_path = os.path.join(project_path, "log")

#接口测试路径
test_path = os.path.join(project_path, "tests")

# 请求超时
timeout = read_config.getValue("Project", "request_timeout")