# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

__version__ = u'0.5.0'


def create_app(config=None):
    from .app import create_app as _create_app

    app = _create_app(config)

    register_extensions(app)
    register_blueprints(app)
    register_error_handlers(app)
    return app


def register_blueprints(app):
    def register(bp):
        prefix = '/{}'.format(bp.name)
        app.register_blueprint(bp, url_prefix=prefix)

    import badwolf.webhook.views
    import badwolf.oauth.views
    import badwolf.log.views

    register(badwolf.webhook.views.blueprint)
    register(badwolf.oauth.views.blueprint)
    register(badwolf.log.views.blueprint)


def register_error_handlers(app):
    pass


def register_extensions(app):
    from .extensions import sentry, mail, bitbucket

    sentry.init_app(app)
    mail.init_app(app)
    bitbucket.init_app(app)
