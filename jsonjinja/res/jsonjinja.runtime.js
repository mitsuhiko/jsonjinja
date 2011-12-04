(function() {
  var global = this;
  var _jsonjinja = global.jsonjinja;
  var templatetk = global.templatetk.noConflict();

  templatetk.config.getTemplate = function(name) {
    return lib.getTemplate(name);
  };

  function simpleRepr(value) {
    if (value instanceof templatetk.rt.Markup)
      return value;
    if (value == null)
      return '';
    if (typeof value === 'boolean' ||
        typeof value === 'number' ||
        typeof value === 'string')
      return '' + value;
    lib.signalError('Cannot print complex objects, tried to print ' +
      Object.prototype.toString.call(value) + ' (' + value + ')');
    return '';
  }

  /* update the escape function to support wire object specified
     HTML safety */
  var escapeFunc = templatetk.rt.escape;
  templatetk.rt.escape = function(value) {
    var wod = lib.grabWireObjectDetails(value);
    if (wod === 'html-safe')
      return templatetk.rt.markSafe(value.value);
    return escapeFunc(simpleRepr(value));
  };

  /* Finalize by default just converts into a string.  We want to make sure
     that if a HTML safe wire object is finalized we only print the value. */
  templatetk.rt.toUnicode = function(value) {
    var wod = lib.grabWireObjectDetails(value);
    if (wod === 'html-safe')
      return value.value;
    return simpleRepr(value);
  };

  var lib = global.jsonjinja = {
    _templateFactories : {},
    _templates : {},

    grabWireObjectDetails : function(object) {
      if (object && typeof object.__jsonjinja_wire__ !== 'undefined')
        return object.__jsonjinja_wire__;
      return null;
    },

    getTemplate : function(name) {
      var tmpl = this._templates[name];
      if (tmpl == null) {
        var factory = this._templateFactories[name];
        if (factory == null)
          return null;
        tmpl = this._registerTemplate(name, factory(templatetk.rt));
      }
      return tmpl;
    },

    addTemplate : function(name, factoryOrTemplate) {
      if (factoryOrTemplate instanceof templatetk.rt.Template) {
        this._registerTemplate(name, factoryOrTemplate);
      } else {
        this._templates[name] = null;
        this._templateFactories[name] = factoryOrTemplate;
      }
    },

    _registerTemplate : function(name, template) {
      delete this._templateFactories[name];
      this._templates[name] = template;
      template.name = name;
      return template;
    },

    removeTemplate : function(name) {
      delete this._templates[name];
      delete this._templateFactories[name];
    },

    listTemplates : function() {
      var rv = [];
      for (var key in this._templates)
        rv.push(key);
      rv.sort();
      return rv;
    },

    addTemplates : function(mapping) {
      for (var key in mapping)
        this.addTemplate(key, mapping[key]);
    },

    templatetk : templatetk,

    signalError : function(message) {
      if (console && console.error)
        console.error(message);
    },

    noConflict : function() {
      global.jsonjinja = _jsonjinja;
      return lib;
    }
  };
})();