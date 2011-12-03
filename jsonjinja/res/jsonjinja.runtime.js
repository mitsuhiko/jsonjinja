(function() {
  var global = this;
  var _jsonjinja = global.jsonjinja;
  var templatetk = global.templatetk.noConflict();

  var config = new templatetk.Config();
  templatetk.defaultConfig = config;
  config.getTemplate = function(name) {
    return lib.getTemplate(name);
  };

  var lib = global.jsonjinja = {
    _templateCache : {},
    _templates : {},

    getTemplate : function(name) {
      var tmpl = this._templateCache[name];
      if (tmpl == null) {
        tmpl = this._templateCache[name] = this._templates[name](templatetk.rt);
        tmpl.name = name;
      }
      return tmpl;
    },

    addTemplate : function(name, factory) {
      this._templates[name] = factory;
      this._templateCache[name] = null;
    },

    removeTemplate : function(name) {
      delete this._templates[name];
      delete this._templateCache[name];
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
