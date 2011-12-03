(function() {
  var global = this;
  var _jsonjinja = global.jsonjinja;
  var templatetk = global.templatetk.noConflict();

  templatetk.config.getTemplate = function(name) {
    return lib.getTemplate(name);
  };

  /* update the escape function to support wire object specified
     HTML safety */
  var escapeFunc = templatetk.rt.escape;
  templatetk.rt.escape = function(value) {
    var wod = lib.grabWireObjectDetails(value);
    if (wod === 'html-safe')
      return templatetk.rt.markSafe(value.value);
    return escapeFunc(value);
  };

  var lib = global.jsonjinja = {
    _templateFactories : {},
    _templates : {},

    grabWireObjectDetails : function(object) {
      if (typeof object.__jsonjinja_wire__ !== 'undefined')
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

    noConflict : function() {
      global.jsonjinja = _jsonjinja;
      return lib;
    }
  };
})();
