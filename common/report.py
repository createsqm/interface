# -  *  - coding:utf-8  -  *  -
import unittest


class HtmlTestResult(unittest.TextTestResult):

    def __init__(self, stream, descriptions, verbosity=1):
        super(HtmlTestResult, self).__init__(stream, descriptions, verbosity)
        self.records = []

    def _record_test(self, test, status):
        data = {
            'name': test.shortDescription(),
            'status': status,
            "datas": test.datas
        }
        self.records.append(data)

    def startTest(self, test):
        """ add start test time """
        super(HtmlTestResult, self).startTest(test)

    def addSuccess(self, test):
        super(HtmlTestResult, self).addSuccess(test)
        self._record_test(test, "Success")
        print(self.records)

    def addFailure(self, test, err):
        super(HtmlTestResult, self).addFailure(test, err)
        self._record_test(test, "failure")

    def addError(self, test, err):
        super(HtmlTestResult, self).addError(test, err)
        self._record_test(test, "error")

    def addSkip(self, test, reason):
        super(HtmlTestResult, self).addSkip(test, "")
        self._record_test(test, "skip")