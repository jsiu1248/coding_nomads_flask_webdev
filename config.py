import os
basedir = os.path.abspath(os.path.dirname(__file__))

class Config():
    SECRET_KEY = os.environ.get('SECRET_KEY') or "the hardest string to guess 3v4r"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Flask-Mail config
    MAIL_SERVER = 'smtp.googlemail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    RAGTIME_ADMIN = os.environ.get('RAGTIME_ADMIN')
    RAGTIME_MAIL_SUBJECT_PREFIX = 'Ragtime —'
    RAGTIME_MAIL_SENDER = f'Ragtime Admin <{RAGTIME_ADMIN}>'

    RAGTIME_COMPS_PER_PAGE = 20
    RAGTIME_FOLLOWERS_PER_PAGE = 20
    RAGTIME_FOLLOWING_PER_PAGE = 20
    RAGTIME_COMMENTS_PER_PAGE = 20

    SSL_REDIRECT = False

    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_DEV_URL') or \
        'sqlite:///' + os.path.join(basedir, 'data-dev.sqlite')
    
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)

        import logging
        from sys import stdout
        console_handler = logging.StreamHandler(stdout)
        console_handler.setLevel(logging.DEBUG)
        app.logger.addHandler(console_handler)


class TestingConfig(Config):
    TESTING = True
    # Unit tests use a SEPARATE database to prevent modifications of
    # development
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_TEST_URL') or \
        'sqlite://'
    SERVER_NAME = 'localhost:5000'


class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'data.sqlite')

    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        # email errors
        import logging
        from logging.handlers import SMTPHandler
        creds = None
        secure = None
        if getattr(cls, 'MAIL_USERNAME', None) is not None:
            creds = (cls.MAIL_USERNAME, cls.MAIL_PASSWORD)
            if getattr(cls, 'MAIL_USE_TLS', None):
                secure = ()
        mail_handler = SMTPHandler(
            mailhost=(cls.MAIL_SERVER, cls.MAIL_PORT),
            fromaddr=cls.RAGTIME_MAIL_SENDER,
            toaddrs=[cls.RAGTIME_ADMIN],
            subject=cls.RAGTIME_MAIL_SUBJECT_PREFIX + " Application Error",
            credentials=creds,
            secure=secure
        )
        mail_handler.setLevel(logging.ERROR)
        app.logger.addHandler(mail_handler)

class HerokuConfig(ProductionConfig):
    SSL_REDIRECT = True if os.environ.get('DYNO') else False

    @classmethod
    def init_app(cls, app):
        ProductionConfig.init_app(app)

        # log to stderr
        import logging
        from logging import StreamHandler
        file_handler = StreamHandler
        file_handler.setLevel(file_handler, level=logging.INFO)
        app.logger.addHandler(file_handler)

        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app)


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'heroku': HerokuConfig,
    'default': DevelopmentConfig
}
