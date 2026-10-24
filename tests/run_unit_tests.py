"""将 unittest 框架回调输出为可被 UT results 读取的 JSON。"""
import inspect
import json
from pathlib import Path
import sys
import unittest


class JsonResult(unittest.TestResult):
    def __init__(self):
        super().__init__()
        self.records = {}

    def record(self, test, status, error=None):
        filename = str(Path(inspect.getfile(type(test))).resolve())
        row = {
            'ancestorTitles': [type(test).__qualname__],
            'title': test._testMethodName,
            'status': status,
            'failureMessages': [] if error is None else [self._exc_info_to_string(error, test)],
        }
        self.records.setdefault(filename, []).append(row)

    def addSuccess(self, test):
        super().addSuccess(test)
        self.record(test, 'passed')

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.record(test, 'failed', err)

    def addError(self, test, err):
        super().addError(test, err)
        self.record(test, 'failed', err)


def main():
    suite = unittest.defaultTestLoader.loadTestsFromNames(sys.argv[1:] or ['tests.test_wiki_tool'])
    result = JsonResult()
    suite.run(result)
    report = {
        'numTotalTests': result.testsRun,
        'numFailedTests': len(result.failures) + len(result.errors),
        'numSkippedTests': len(result.skipped),
        'testResults': [{'name': name, 'assertionResults': rows}
                        for name, rows in result.records.items()],
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return int(not result.wasSuccessful() or result.testsRun == 0)


if __name__ == '__main__':
    sys.exit(main())
