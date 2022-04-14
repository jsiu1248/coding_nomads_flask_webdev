from flask import render_template, request, jsonify
from werkzeug.exceptions import NotFound, InternalServerError, Forbidden
from . import main

@main.app_errorhandler(NotFound)
def page_not_found(e):
    if request.accept_mimetypes.accept_json and \
            not request.accept_mimetypes.accept_html:
        response = jsonify({'error': 'not found'})
        response.status_code = 404
        return response
    error_msg="That page doesn't exist."
    return render_template('error.html', error_msg=error_msg), 404


@main.app_errorhandler(InternalServerError)
def internal_server_error(e):
    if request.accept_mimetypes.accept_json and \
            not request.accept_mimetypes.accept_html:
        response = jsonify({'error': 'internal server error'})
        response.status_code = 500
        return response
    error_msg="Sorry, we seem to be experiencing some technical difficulties. Please try again later."
    return render_template("error.html", error_msg=error_msg), 500


@main.app_errorhandler(Forbidden)
def forbidden(e):
    if request.accept_mimetypes.accept_json and \
            not request.accept_mimetypes.accept_html:
        response = jsonify({'error': 'forbidden'})
        response.status_code = 403
        return response
    error_msg="This page is forbidden, you're not supposed to be here. Shoo, off you go!"
    return render_template("error.html", error_msg=error_msg), 403
