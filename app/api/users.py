from flask import jsonify, url_for, request, g, current_app
from . import api
from ..models import User, Composition


@api.route('/users/<int:id>')
def get_user(id):
    user = User.query.get_or_404(id)
    return jsonify(user.to_json())


@api.route('/users/<int:id>/compositions/')
def get_user_compositions(id):
    user = User.query.get_or_404(id)
    page = request.args.get('page', 1, type=int)
    pagination = user.compositions.order_by(Composition.timestamp.desc()).paginate(
        page,
        per_page=current_app.config['RAGTIME_COMPS_PER_PAGE'],
        error_out=False)
    compositions = pagination.items
    prev = None
    if pagination.has_prev:
        prev = url_for('api.get_user_compositions', id=id, page=page-1)
    next = None
    if pagination.has_next:
        next = url_for('api.get_user_compositions', id=id, page=page+1)
    return jsonify({
        'compositions': [composition.to_json() for composition in compositions],
        'prev': prev,
        'next': next,
        'count': pagination.total
    })


@api.route('/users/<int:id>/timeline/')
def get_user_followed(id):
    user = User.query.get_or_404(id)
    page = request.args.get('page', 1, type=int)
    pagination = user.followed_compositions.order_by(Composition.timestamp.desc()).paginate(
        page,
        per_page=current_app.config['RAGTIME_COMPS_PER_PAGE'],
        error_out=False)
    compositions = pagination.items
    prev = None
    if pagination.has_prev:
        prev = url_for('api.get_user_compositions', id=id, page=page-1)
    next = None
    if pagination.has_next:
        next = url_for('api.get_user_compositions', id=id, page=page+1)
    return jsonify({
        'compositions': [composition.to_json() for composition in compositions],
        'prev': prev,
        'next': next,
        'count': pagination.total
    })