#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re

from flask import Blueprint, current_app, url_for

__version__ = '0.8.1'

BULMA_VERSION = re.sub(r'^(\d+\.\d+\.\d+).*', r'\1', __version__)
JQUERY_VERSION = '3.4.1'

class CDN(object):
    def get_resource_url(self, filename):
        raise NotImplementedError

class StaticCDN(object):
    def __init__(self,static_endpoint='static', rev=False):
        self.static_endpoint = static_endpoint
        self.rev = rev

    def get_resource_url(self, filename):
        extra_args = {}

        if self.rev and current_app.config['BULMA_QUERYSTRING_REVVING']:
            extra_args['bulma'] = __version__

        return url_for(self.static_endpoint, filename=filename, **extra_args)

class WebCDN(object):
    def __init__(self, baseurl):
        self.baseurl = baseurl

    def get_resource_url(self, filename):
        return self.baseurl + filename

class ConditionalCDN(object):
    def __init__(self, confvar, primary, fallback):
        self.confvar = confvar
        self.primary = primary
        self.fallback = fallback

    def get_resource_url(self, filename):
        if current_app.config[self.confvar]:
            return self.primary.get_resource_url(filename)
        return self.fallback.get_resource_url(filename)

def bulma_find_resource(filename, cdn, use_minified=None, local=True):
    config = current_app.config

    if None == use_minified:
        use_minified = config['BULMA_USE_MINIFIED']

    if use_minified:
        filename = '%s.min.%s' % tuple(filename.rsplit('.', 1))

    cdns = current_app.extensions['bulma']['cdns']
    resource_url = cdns[cdn].get_resource_url(filename)

    if resource_url.startswith('//') and config['BULMA_CDN_FORCE_SSL']:
        resource_url = f'https:{resource_url}'

    return resource_url

class Bulma(object):
    def __init__(self, app=None):
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        app.config.setdefault('BULMA_USE_MINIFIED', True)
        app.config.setdefault('BULMA_CDN_FORCE_SSL', True)

        app.config.setdefault('BULMA_QUERYSTRING_REVVING', True)
        app.config.setdefault('BULMA_SERVE_LOCAL', False)

        app.config.setdefault('BULMA_LOCAL_SUBDOMAIN', None)

        blueprint = Blueprint(
            'bulma',
            __name__,
            template_folder='templates',
            static_folder='static',
            static_url_path= f'{app.static_url_path}/bulma',
            subdomain=app.config['BULMA_LOCAL_SUBDOMAIN'])

        app.register_blueprint(blueprint)

        app.jinja_env.globals['bulma_find_resource'] = bulma_find_resource
        app.jinja_env.add_extension('jinja2.ext.do')

        if not hasattr(app, 'extensions'):
            app.extensions = {}

        local = StaticCDN('bulma.static', rev=True)
        static = StaticCDN()

        def lwrap(cdn, primary=static):
            return ConditionalCDN('BULMA_SERVE_LOCAL', primary, cdn)

        bulma = lwrap(
            WebCDN('//cdn.jsdelivr.net/npm/package/bulma@%s/' %
                   BULMA_VERSION), local)

        jquery = lwrap(
            WebCDN('//cdn.jsdelivr.net/npm/package/jquery@%s/' %
                   JQUERY_VERSION), local)

        app.extensions['bulma'] = {
            'cdns': {
                'local': local,
                'static': static,
                'bulma': bulma,
                'jquery': jquery,
            },
        }
