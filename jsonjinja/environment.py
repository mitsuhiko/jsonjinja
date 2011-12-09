from cStringIO import StringIO
from jsonjinja.config import Config
from jsonjinja.lexer import Lexer
from jsonjinja.parser import Parser
from jsonjinja.utils import ensure_json_compatible
from templatetk.jscompiler import to_javascript
from templatetk.asttransform import to_ast
from templatetk.bcinterp import run_bytecode, RuntimeState, compile_ast
from templatetk.utils import json


class Template(object):

    def __init__(self, name, config, code):
        namespace = run_bytecode(code)
        self.config = config
        self.name = name
        self.filename = code.co_filename
        self.setup_func = namespace['setup']
        self.root_func = namespace['root']

    def execute(self, context, info=None):
        rtstate = RuntimeState(context, self.config, self.name, info)
        self.setup_func(rtstate)
        return self.root_func(rtstate)

    def render(self, *args, **kwargs):
        if not args:
            context = {}
        elif len(args) == 1:
            context = args[0]
            if isinstance(context, basestring):
                context = json.loads(context)
            elif hasattr(context, 'read'):
                context = json.load(context)
            else:
                context = dict(context)
        if kwargs:
            context.update(kwargs)
        if __debug__:
            ensure_json_compatible(context)
        return u''.join(self.execute(context))


class Environment(object):
    lexer = Lexer()
    template_class = Template

    def __init__(self, loader=None):
        self.config = Config(self)
        self.loader = loader
        self.filters = {}

    def compile_javascript_templates(self, filter_func=None, stream=None):
        write_out = False
        if stream is None:
            stream = StringIO()
            write_out = True
        stream.write('{')
        first = True
        for template_name in self.loader.list_templates():
            if filter_func is not None and not filter_func(template_name):
                continue
            if not first:
                stream.write(',')
            stream.write('%s:' % json.dumps(template_name))
            node = self.get_template_as_node(template_name)
            to_javascript(node, stream)
            first = False
        stream.write('}')
        if write_out:
            return stream.getvalue()

    def get_template_as_node(self, name):
        contents, filename, uptodate = self.loader.get_source(self, name)
        return self.parse(contents, name, filename)

    def get_template(self, name):
        return self.loader.load(self, name)

    def parse(self, source, name, filename=None):
        return Parser(self.config, source, name, filename).parse()

    def compile(self, source, name, filename=None):
        node = self.parse(source, name, filename)
        ast = to_ast(node)
        if filename is None:
            filename = '<string>'
        return compile_ast(ast, filename)
