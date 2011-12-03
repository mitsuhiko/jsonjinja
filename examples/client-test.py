import os
import sys
import templatetk
import jsonjinja


runtime_js = [
    os.path.join(os.path.dirname(templatetk.__file__),
                 'res', 'templatetk.runtime.js'),
    os.path.join(os.path.dirname(jsonjinja.__file__),
                 'res', 'jsonjinja.runtime.js')
]


env = jsonjinja.Environment(loader=jsonjinja.DictLoader({
    'layout.html': '''\
<!doctype html>
<title>{% block title %}{% endblock %}</title>
{% block body %}{% endblock %}
''',
    'test.html': '''\
{% extends "layout.html" %}
{% block title %}Index{% endblock %}
{% block body %}
  <h1>Testing</h1>
  <ul>
  {% for item in seq %}
    <li>{{ loop.index }} - {{ item }}
  {% endfor %}
  </ul>
{% endblock %}
}))
'''}))


print '<!doctype html>'
print '<script type=text/javascript>'
for filename in runtime_js:
    with open(filename) as f:
        print f.read()
print 'jsonjinja.addTemplates('
env.compile_javascript_templates(stream=sys.stdout)
print ');'
print 'document.write(jsonjinja.getTemplate("test.html").render({seq: [1, 2, 3]}));'
print '</script>'
