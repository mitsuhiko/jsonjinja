(function() {
  var global = this;
  var _jsonjinja = global.jsonjinja;
  var templatetk = global.templatetk.noConflict();
  var hasOwnProperty = Object.prototype.hasOwnProperty;

  templatetk.config.getTemplate = function(name) {
    return lib.getTemplate(name);
  };

  templatetk.config.getAutoEscapeDefault = function(name) {
    return !!name.match(/\.(html|xml)$/);
  };

  templatetk.rt.sequenceFromObject = function(obj) {
    var rv = [];
    for (var key in obj)
      if (hasOwnProperty.call(obj, key))
        rv.push([key, obj[key]]);
    rv.sort();
    return rv;
  };

  templatetk.rt.markSafe = function(value) {
    return {__jsonjinja_wire__: 'html-safe', value: value};
  };

  templatetk.rt.concat = function(info, pieces) {
    var rv = [];
    for (var i = 0, n = pieces.length; i != n; i++)
      rv.push(info.finalize(pieces[i]));
    rv = rv.join('');
    return info.autoescape ? this.markSafe(rv) : rv;
  };

  templatetk.rt.finalize = function(value, autoescape) {
    if (value == null)
      return '';
    if (typeof value === 'boolean' ||
        typeof value === 'number')
      return '' + value;
    var wod = lib.grabWireObjectDetails(value);
    if (wod === 'html-safe')
      return value.value;
    if (value instanceof Array ||
        (value.prototype && value.prototype.toString === Object.prototype.toString))
      lib.signalError('Cannot print complex objects, tried to print ' +
        Object.prototype.toString.call(value) + ' (' + value + ')');
    if (autoescape)
      return templatetk.utils.escape(value);
    return '' + value;
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
