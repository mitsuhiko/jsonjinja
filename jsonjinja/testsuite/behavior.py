# -*- coding: utf-8 -*-
"""
    jsonjinja.testsuite.behavior
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Basic behavior.

    :copyright: (c) 2011 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
import os
import unittest
import subprocess
import tempfile
from cStringIO import StringIO

from jsonjinja.testsuite import JSONJinjaTestCase
from jsonjinja.environment import Environment
from jsonjinja.loaders import FileSystemLoader
from jsonjinja.utils import get_runtime_javascript
from templatetk.utils import json


template_path = os.path.join(os.path.dirname(__file__), 'behavior')
template_exts = ('.html', '.txt')
env = Environment(loader=FileSystemLoader([template_path]))
_common_js = None


class BaseTestCase(JSONJinjaTestCase):

    def run_behavior_test(self, template_filename):
        base_filename = template_filename.rsplit('.', 1)[0]
        with open(base_filename + '.json') as f:
            context = json.load(f)
        with open(base_filename + '.output') as f:
            expected_output = f.read()
            if expected_output[-1] == '\n':
                expected_output = expected_output[:-1]
        output = self.evaluate_template(os.path.basename(template_filename),
                                        context)
        self.assert_equal(expected_output, output)


def make_behavior_testcase():
    class BehaviorTestCase(BaseTestCase):
        pass

    def add_test(filename):
        method = 'test_' + os.path.basename(filename.rsplit('.', 1)[0])
        def test_method(self):
            self.run_behavior_test(filename)
        setattr(BehaviorTestCase, method, test_method)

    for filename in os.listdir(template_path):
        if filename.endswith(template_exts):
            add_test(os.path.join(template_path, filename))

    return BehaviorTestCase
BehaviorTestCase = make_behavior_testcase()


class PythonTestCase(BehaviorTestCase):

    def evaluate_template(self, load_name, context):
        tmpl = env.get_template(load_name)
        return tmpl.render(context)


class JavaScriptTestCase(BehaviorTestCase):
    _common_js = None

    @classmethod
    def get_common_javascript(cls):
        if cls._common_js is not None:
            return cls._common_js
        def filter_func(filename):
            return filename.endswith(template_exts)

        f = StringIO()
        f.write(get_runtime_javascript())
        f.write('jsonjinja.addTemplates(')
        env.compile_javascript_templates(filter_func=filter_func,
                                         stream=f)
        f.write(');\n')

        rv = cls._common_js = f.getvalue()
        return rv

    def evaluate_template(self, load_name, context):
        fd, filename = tempfile.mkstemp(text=True)
        f = os.fdopen(fd, 'w')
        try:
            f.write(self.get_common_javascript())
            f.write('''
                var tmpl = jsonjinja.getTemplate(%s);
                process.stdout.write(tmpl.render(%s));
            ''' % (json.dumps(load_name), json.dumps(context)))
            f.close()
            c = subprocess.Popen(['node', filename], stdout=subprocess.PIPE)
            stdout, stderr = c.communicate()
        finally:
            os.remove(filename)
        return stdout


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(PythonTestCase))
    suite.addTest(unittest.makeSuite(JavaScriptTestCase))
    return suite
