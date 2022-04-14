import bleach
import logging
from functools import wraps
from flask import abort, request, current_app
from flask_login import current_user
from .models import Permission

def log_visit(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        logger: logging.Logger = None
        msg = f"Visiting function {f.__name__}()."
        if current_app:
            logger = current_app.logger
            if request:
                msg += f" Endpoint: {request.endpoint}"
        if logger:
            logger.debug(msg)
        return f(*args, **kwargs)
    return decorated_function

def clean_and_linkify(f):
    @wraps(f)
    def decorated_function(target, value, oldvalue, initiator, *args, **kwargs):
        return f(target, value, oldvalue, initiator, *args, **kwargs)
    return decorated_function

def permission_required(permission):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.can(permission):
                import traceback
                traceback.print_stack()
                print(current_user)
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def admin_required(f):
    return permission_required(Permission.ADMIN)(f)