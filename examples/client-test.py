import sys
import jsonjinja
from jsonjinja.utils import get_runtime_javascript


env = jsonjinja.Environment(loader=jsonjinja.DictLoader({
    'layout.html': '''\
<!doctype html>
<title>{% block title %}{% endblock %}</title>
<div class=body>
{% block body %}{% endblock %}
</div>
''',
    'test.html': '''\
{% extends "layout.html" %}
{% block title %}{{ title }}{% endblock %}
{% block body %}
  <h1>Testing</h1>
  <ul>
  {% for item in seq %}
    <li>{{ loop.index }} - {{ item }} [{{ loop.cycle("odd", "even") }}]
  {% endfor %}
  </ul>
{% endblock %}
}))
'''}))


print '<!doctype html>'
print '<script type=text/javascript src=jquery.js></script>'
print '<script type=text/javascript>'
print get_runtime_javascript()
print 'jsonjinja.addTemplates('
env.compile_javascript_templates(stream=sys.stdout)
print ');'
print 'document.write(jsonjinja.getTemplate("test.html").render({seq: [1, 2, 3], title: "Foo"}));'
print '</script>'
