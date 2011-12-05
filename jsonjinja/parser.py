from templatetk import nodes
from jsonjinja.exceptions import TemplateSyntaxError, TemplateAssertionError
from jsonjinja.lexer import describe_token, describe_token_expr


_statement_keywords = frozenset(['for', 'if', 'block', 'extends', 'print',
                                 'macro', 'from', 'import'])
_compare_operators = frozenset(['eq', 'ne', 'lt', 'lteq', 'gt', 'gteq'])


class Parser(object):
    """This is the central parsing class Jinja2 uses.  It's passed to
    extensions and can be used to parse expressions or statements.
    """

    def __init__(self, config, source, name=None, filename=None,
                 state=None):
        self.config = config
        self.stream = config.environment.lexer.tokenize(source,
            name, filename, state)
        self.name = name
        self.filename = filename
        self.closed = False
        self._last_identifier = 0
        self._tag_stack = []
        self._end_token_stack = []

    def fail(self, msg, lineno=None, exc=TemplateSyntaxError):
        """Convenience method that raises `exc` with the message, passed
        line number or last line number as well as the current name and
        filename.
        """
        if lineno is None:
            lineno = self.stream.current.lineno
        raise exc(msg, lineno, self.name, self.filename)

    def _fail_ut_eof(self, name, end_token_stack, lineno):
        expected = []
        for exprs in end_token_stack:
            expected.extend(map(describe_token_expr, exprs))
        if end_token_stack:
            currently_looking = ' or '.join(
                "'%s'" % describe_token_expr(expr)
                for expr in end_token_stack[-1])
        else:
            currently_looking = None

        if name is None:
            message = ['Unexpected end of template.']
        else:
            message = ['Encountered unknown tag \'%s\'.' % name]

        if currently_looking:
            if name is not None and name in expected:
                message.append('You probably made a nesting mistake. Jinja '
                               'is expecting this tag, but currently looking '
                               'for %s.' % currently_looking)
            else:
                message.append('Jinja was looking for the following tags: '
                               '%s.' % currently_looking)

        if self._tag_stack:
            message.append('The innermost block that needs to be '
                           'closed is \'%s\'.' % self._tag_stack[-1])

        self.fail(' '.join(message), lineno)

    def fail_unknown_tag(self, name, lineno=None):
        """Called if the parser encounters an unknown tag.  Tries to fail
        with a human readable error message that could help to identify
        the problem.
        """
        return self._fail_ut_eof(name, self._end_token_stack, lineno)

    def fail_eof(self, end_tokens=None, lineno=None):
        """Like fail_unknown_tag but for end of template situations."""
        stack = list(self._end_token_stack)
        if end_tokens is not None:
            stack.append(end_tokens)
        return self._fail_ut_eof(None, stack, lineno)

    def is_tuple_end(self, extra_end_rules=None):
        """Are we at the end of a tuple?"""
        if self.stream.current.type in ('variable_end', 'block_end', 'rparen'):
            return True
        elif extra_end_rules is not None:
            return self.stream.current.test_any(extra_end_rules)
        return False

    def free_identifier(self, lineno=None):
        """Return a new free identifier as :class:`~jinja2.nodes.InternalName`."""
        self._last_identifier += 1
        rv = object.__new__(nodes.InternalName)
        nodes.Node.__init__(rv, 'fi%d' % self._last_identifier, lineno=lineno)
        return rv

    def parse_statement(self):
        """Parse a single statement."""
        token = self.stream.current
        if token.type != 'name':
            self.fail('tag name expected', token.lineno)
        self._tag_stack.append(token.value)
        pop_tag = True
        try:
            if token.value in _statement_keywords:
                return getattr(self, 'parse_' + self.stream.current.value)()
            if token.value == 'call':
                return self.parse_call_block()
            if token.value == 'filter':
                return self.parse_filter_block()
            ext = self.extensions.get(token.value)
            if ext is not None:
                return ext(self)

            # did not work out, remove the token we pushed by accident
            # from the stack so that the unknown tag fail function can
            # produce a proper error message.
            self._tag_stack.pop()
            pop_tag = False
            self.fail_unknown_tag(token.value, token.lineno)
        finally:
            if pop_tag:
                self._tag_stack.pop()

    def parse_statements(self, end_tokens, drop_needle=False):
        """Parse multiple statements into a list until one of the end tokens
        is reached.  This is used to parse the body of statements as it also
        parses template data if appropriate.  The parser checks first if the
        current token is a colon and skips it if there is one.  Then it checks
        for the block end and parses until if one of the `end_tokens` is
        reached.  Per default the active token in the stream at the end of
        the call is the matched end token.  If this is not wanted `drop_needle`
        can be set to `True` and the end token is removed.
        """
        # the first token may be a colon for python compatibility
        self.stream.skip_if('colon')

        # in the future it would be possible to add whole code sections
        # by adding some sort of end of statement token and parsing those here.
        self.stream.expect('block_end')
        result = self.subparse(end_tokens)

        # we reached the end of the template too early, the subparser
        # does not check for this, so we do that now
        if self.stream.current.type == 'eof':
            self.fail_eof(end_tokens)

        if drop_needle:
            self.stream.next()
        return result

    def parse_for(self):
        """Parse a for loop."""
        lineno = self.stream.expect('name:for').lineno
        target = self.parse_assign_target(extra_end_rules=('name:in',))
        self.stream.expect('name:in')
        iter = self.parse_expression()
        body = self.parse_statements(('name:endfor', 'name:else'))
        if self.stream.next().value == 'endfor':
            else_ = []
        else:
            else_ = self.parse_statements(('name:endfor',), drop_needle=True)
        return nodes.For(target, iter, body, else_, lineno=lineno)

    def parse_if(self):
        """Parse an if construct."""
        node = result = nodes.If(lineno=self.stream.expect('name:if').lineno)
        while 1:
            node.test = self.parse_expression()
            node.body = self.parse_statements(('name:elif', 'name:else',
                                               'name:endif'))
            token = self.stream.next()
            if token.test('name:elif'):
                new_node = nodes.If(lineno=self.stream.current.lineno)
                node.else_ = [new_node]
                node = new_node
                continue
            elif token.test('name:else'):
                node.else_ = self.parse_statements(('name:endif',),
                                                   drop_needle=True)
            else:
                node.else_ = []
            break
        return result

    def parse_block(self):
        node = nodes.Block(lineno=self.stream.next().lineno)
        node.name = self.stream.expect('name').value

        # common problem people encounter when switching from django
        # to jinja.  we do not support hyphens in block names, so let's
        # raise a nicer error message in that case.
        if self.stream.current.type == 'sub':
            self.fail('Block names in Jinja have to be valid Python '
                      'identifiers and may not contain hyphens, use an '
                      'underscore instead.')

        node.body = self.parse_statements(('name:endblock',), drop_needle=True)
        self.stream.skip_if('name:' + node.name)
        return node

    def parse_extends(self):
        node = nodes.Extends(lineno=self.stream.next().lineno)
        node.template = self.parse_expression()
        return node

    def parse_import(self):
        node = nodes.Import(lineno=self.stream.next().lineno)
        node.template = self.parse_expression()
        self.stream.expect('name:as')
        node.target = self.parse_assign_target(name_only=True).name
        return node

    def parse_from(self):
        node = nodes.FromImport(lineno=self.stream.next().lineno)
        node.template = self.parse_expression()
        self.stream.expect('name:import')
        node.names = []

        while 1:
            if node.names:
                self.stream.expect('comma')
            if self.stream.current.type == 'name':
                target = self.parse_assign_target(name_only=True)
                if target.name.startswith('_'):
                    self.fail('names starting with an underline can not '
                              'be imported', target.lineno,
                              exc=TemplateAssertionError)
                if self.stream.skip_if('name:as'):
                    alias = self.parse_assign_target(name_only=True)
                    node.names.append((target.name, alias.name))
                else:
                    node.names.append(target.name)
                if self.stream.current.type != 'comma':
                    break
            else:
                break
        return node

    def parse_signature(self, node):
        node.args = args = []
        node.defaults = defaults = []
        self.stream.expect('lparen')
        while self.stream.current.type != 'rparen':
            if args:
                self.stream.expect('comma')
            arg = self.parse_assign_target(name_only=True, ctx='param')
            if self.stream.skip_if('assign'):
                defaults.append(self.parse_expression())
            args.append(arg)
        self.stream.expect('rparen')

    def parse_call_block(self):
        node = nodes.CallBlock(lineno=next(self.stream).lineno)
        if self.stream.current.type == 'lparen':
            self.parse_signature(node)
        else:
            node.args = []
            node.defaults = []

        node.call = self.parse_expression()
        if not isinstance(node.call, nodes.Call):
            self.fail('expected call', node.lineno)
        node.body = self.parse_statements(('name:endcall',), drop_needle=True)
        return node

    def parse_filter_block(self):
        node = nodes.FilterBlock(lineno=next(self.stream).lineno)
        node.filter = self.parse_filter(None, start_inline=True)
        node.body = self.parse_statements(('name:endfilter',),
                                          drop_needle=True)
        return node

    def parse_macro(self):
        lineno = self.stream.next().lineno
        node = nodes.Function()
        macro_name = self.parse_assign_target(name_only=True).name
        node.name = nodes.Const(macro_name)
        self.parse_signature(node)
        node.body = self.parse_statements(('name:endmacro',),
                                          drop_needle=True)
        return nodes.Assign(nodes.Name(macro_name, 'store'), node,
                            lineno=lineno)

    def parse_print(self):
        node = nodes.Output(lineno=next(self.stream).lineno)
        node.nodes = []
        while self.stream.current.type != 'block_end':
            if node.nodes:
                self.stream.expect('comma')
            node.nodes.append(self.parse_expression())
        return node

    def parse_assign_target(self, with_tuple=True, name_only=False,
                            extra_end_rules=None, ctx='store'):
        def parse_name():
            token = self.stream.expect('name')
            return nodes.Name(token.value, ctx, lineno=token.lineno)
        def parse_tuple_expr():
            lineno = self.stream.current.lineno
            args = []
            is_tuple = False
            while 1:
                if args:
                    self.stream.expect('comma')
                if self.is_tuple_end(extra_end_rules):
                    break
                if self.stream.skip_if('lparen'):
                    args.append(parse_tuple_expr())
                    self.stream.expect('rparen')
                else:
                    args.append(parse_name())
                if self.stream.current.type == 'comma':
                    is_tuple = True
                else:
                    break
            if not is_tuple:
                if args:
                    return args[0]
                self.fail('Expected an expression, got \'%s\'' %
                          describe_token(self.stream.current))
            return nodes.Tuple(args, ctx, lineno=lineno)

        if name_only:
            target = parse_name()
        else:
            target = parse_tuple_expr()
        if not target.can_assign():
            self.fail('can\'t assign to %r' % target.__class__.
                      __name__.lower(), target.lineno)
        return target

    def parse_expression(self, with_condexpr=True):
        """Parse an expression.  Per default all expressions are parsed, if
        the optional `with_condexpr` parameter is set to `False` conditional
        expressions are not parsed.
        """
        if with_condexpr:
            return self.parse_condexpr()
        return self.parse_or()

    def parse_condexpr(self):
        lineno = self.stream.current.lineno
        expr1 = self.parse_or()
        while self.stream.skip_if('name:if'):
            expr2 = self.parse_or()
            if self.stream.skip_if('name:else'):
                expr3 = self.parse_condexpr()
            else:
                expr3 = None
            expr1 = nodes.CondExpr(expr2, expr1, expr3, lineno=lineno)
            lineno = self.stream.current.lineno
        return expr1

    def parse_or(self):
        lineno = self.stream.current.lineno
        left = self.parse_and()
        while self.stream.skip_if('name:or'):
            right = self.parse_and()
            left = nodes.Or(left, right, lineno=lineno)
            lineno = self.stream.current.lineno
        return left

    def parse_and(self):
        lineno = self.stream.current.lineno
        left = self.parse_not()
        while self.stream.skip_if('name:and'):
            right = self.parse_not()
            left = nodes.And(left, right, lineno=lineno)
            lineno = self.stream.current.lineno
        return left

    def parse_not(self):
        if self.stream.current.test('name:not'):
            lineno = self.stream.next().lineno
            return nodes.Not(self.parse_not(), lineno=lineno)
        return self.parse_compare()

    def parse_compare(self):
        lineno = self.stream.current.lineno
        expr = self.parse_concat()
        ops = []
        while 1:
            token_type = self.stream.current.type
            if token_type in _compare_operators:
                self.stream.next()
                ops.append(nodes.Operand(token_type, self.parse_concat()))
            elif self.stream.skip_if('name:in'):
                ops.append(nodes.Operand('in', self.parse_concat()))
            elif self.stream.current.test('name:not') and \
                 self.stream.look().test('name:in'):
                self.stream.skip(2)
                ops.append(nodes.Operand('notin', self.parse_concat()))
            else:
                break
            lineno = self.stream.current.lineno
        if not ops:
            return expr
        return nodes.Compare(expr, ops, lineno=lineno)

    def parse_concat(self):
        lineno = self.stream.current.lineno
        args = [self.parse_unary()]
        while self.stream.current.type == 'tilde':
            self.stream.next()
            args.append(self.parse_unary())
        if len(args) == 1:
            return args[0]
        return nodes.Concat(args, lineno=lineno)

    def parse_unary(self):
        # Left over from Jinja2 which had unary expressions
        token_type = self.stream.current.type
        lineno = self.stream.current.lineno
        node = self.parse_primary()
        node = self.parse_postfix(node)
        node = self.parse_filter_expr(node)
        return node

    def parse_primary(self):
        token = self.stream.current
        if token.type == 'name':
            if token.value in ('true', 'false', 'True', 'False'):
                node = nodes.Const(token.value in ('true', 'True'),
                                   lineno=token.lineno)
            elif token.value in ('none', 'None'):
                node = nodes.Const(None, lineno=token.lineno)
            else:
                node = nodes.Name(token.value, 'load', lineno=token.lineno)
            self.stream.next()
        elif token.type == 'string':
            self.stream.next()
            buf = [token.value]
            lineno = token.lineno
            while self.stream.current.type == 'string':
                buf.append(self.stream.current.value)
                self.stream.next()
            node = nodes.Const(''.join(buf), lineno=lineno)
        elif token.type in ('integer', 'float'):
            self.stream.next()
            node = nodes.Const(token.value, lineno=token.lineno)
        elif token.type == 'lbracket':
            node = self.parse_list()
        elif token.type == 'lbrace':
            node = self.parse_dict()
        else:
            self.fail("unexpected '%s'" % describe_token(token), token.lineno)
        return node

    def parse_list(self):
        token = self.stream.expect('lbracket')
        items = []
        while self.stream.current.type != 'rbracket':
            if items:
                self.stream.expect('comma')
            if self.stream.current.type == 'rbracket':
                break
            items.append(self.parse_expression())
        self.stream.expect('rbracket')
        return nodes.List(items, lineno=token.lineno)

    def parse_dict(self):
        token = self.stream.expect('lbrace')
        items = []
        while self.stream.current.type != 'rbrace':
            if items:
                self.stream.expect('comma')
            if self.stream.current.type == 'rbrace':
                break
            if self.stream.current.type not in ('string', 'integer'):
                self.fail('Dictionary keys have to be strings or integers')
            key = self.parse_primary()
            self.stream.expect('colon')
            value = self.parse_expression()
            items.append(nodes.Pair(key, value, lineno=key.lineno))
        self.stream.expect('rbrace')
        return nodes.Dict(items, lineno=token.lineno)

    def parse_postfix(self, node):
        while 1:
            token_type = self.stream.current.type
            if token_type == 'dot' or token_type == 'lbracket':
                node = self.parse_subscript(node)
            # calls are valid both after postfix expressions (getattr
            # and getitem) as well as filters and tests
            elif token_type == 'lparen':
                node = self.parse_call(node)
            else:
                break
        return node

    def parse_filter_expr(self, node):
        while 1:
            token_type = self.stream.current.type
            if token_type == 'pipe':
                node = self.parse_filter(node)
            # calls are valid both after postfix expressions (getattr
            # and getitem) as well as filters and tests
            elif token_type == 'lparen':
                node = self.parse_call(node)
            else:
                break
        return node

    def parse_subscript(self, node):
        token = self.stream.next()
        if token.type == 'dot':
            attr_token = self.stream.current
            self.stream.next()
            if attr_token.type == 'name':
                return nodes.Getattr(node, nodes.Const(attr_token.value),
                                     lineno=token.lineno)
            elif attr_token.type != 'integer':
                self.fail('expected name or number', attr_token.lineno)
            arg = nodes.Const(attr_token.value, lineno=attr_token.lineno)
            return nodes.Getitem(node, arg, 'load', lineno=token.lineno)
        if token.type == 'lbracket':
            args = []
            while self.stream.current.type != 'rbracket':
                if args:
                    self.stream.expect('comma')
                args.append(self.parse_subscribed())
            self.stream.expect('rbracket')
            if len(args) == 1:
                arg = args[0]
            else:
                arg = nodes.Tuple(args, 'load', lineno=token.lineno)
            return nodes.Getitem(node, arg, lineno=token.lineno)
        self.fail('expected subscript expression', self.lineno)

    def parse_subscribed(self):
        return self.parse_expression()

    def parse_call(self, node):
        token = self.stream.expect('lparen')
        args = []
        require_comma = False

        def ensure(expr):
            if not expr:
                self.fail('invalid syntax for function call expression',
                          token.lineno)

        while self.stream.current.type != 'rparen':
            if require_comma:
                self.stream.expect('comma')
                # support for trailing comma
                if self.stream.current.type == 'rparen':
                    break
            args.append(self.parse_expression())
            require_comma = True
        self.stream.expect('rparen')

        if node is None:
            return args
        return nodes.Call(node, args, [], None, None,
                          lineno=token.lineno)

    def parse_filter(self, node, start_inline=False):
        while self.stream.current.type == 'pipe' or start_inline:
            if not start_inline:
                self.stream.next()
            token = self.stream.expect('name')
            name = token.value
            while self.stream.current.type == 'dot':
                self.stream.next()
                name += '.' + self.stream.expect('name').value
            if self.stream.current.type == 'lparen':
                args = self.parse_call(None)
            else:
                args = []
            node = nodes.Filter(node, name, args, [], None, None,
                                lineno=token.lineno)
            start_inline = False
        return node

    def subparse(self, end_tokens=None):
        body = []
        data_buffer = []
        add_data = data_buffer.append

        if end_tokens is not None:
            self._end_token_stack.append(end_tokens)

        def flush_data():
            if data_buffer:
                lineno = data_buffer[0].lineno
                body.append(nodes.Output(data_buffer[:], lineno=lineno))
                del data_buffer[:]

        try:
            while self.stream:
                token = self.stream.current
                if token.type == 'data':
                    if token.value:
                        add_data(nodes.TemplateData(token.value,
                                                    lineno=token.lineno))
                    self.stream.next()
                elif token.type == 'variable_begin':
                    self.stream.next()
                    add_data(self.parse_expression())
                    self.stream.expect('variable_end')
                elif token.type == 'block_begin':
                    flush_data()
                    self.stream.next()
                    if end_tokens is not None and \
                       self.stream.current.test_any(*end_tokens):
                        return body
                    rv = self.parse_statement()
                    if isinstance(rv, list):
                        body.extend(rv)
                    else:
                        body.append(rv)
                    self.stream.expect('block_end')
                else:
                    raise AssertionError('internal parsing error')

            flush_data()
        finally:
            if end_tokens is not None:
                self._end_token_stack.pop()

        return body

    def parse(self):
        """Parse the whole template into a `Template` node."""
        result = nodes.Template(self.subparse(), lineno=1)
        result.set_config(self.config)
        return result
