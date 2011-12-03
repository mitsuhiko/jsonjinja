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
    _templateFactories : {},
    _templates : {},

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
