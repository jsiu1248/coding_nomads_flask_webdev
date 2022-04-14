from flask import request, g, url_for, jsonify, current_app
from app import db
from . import api
from .decorators import permission_required
from ..models import Comment, Composition, Permission


@api.route('/comments/')
def get_comments():
    page = request.args.get('page', 1, type=int)
    pagination = Comment.query.paginate(
        page,
        per_page=current_app.config['RAGTIME_COMMENTS_PER_PAGE'],
        error_out=False)
    comments = pagination.items
    prev = None
    if pagination.has_prev:
        prev = url_for('api.get_comments', page=page-1)
    next = None
    if pagination.has_next:
        next = url_for('api.get_comments', page=page+1)
    return jsonify({
        'comments': [comment.to_json() for comment in comment],
        'prev': prev,
        'next': next,
        'count': pagination.total
    })


@api.route('/comments/<int:id>')
def get_comment(id):
    comment = Comment.query.get_or_404(id)
    return jsonify(comment.to_json())


@api.route('/compositions/<int:id>/comments/')
def get_composition_comments(id):
    composition = Composition.query.get_or_404(id)
    page = request.args.get('page', 1, type=int)
    pagination = composition.comments.order_by(Comment.timestamp.asc()).paginate(
        page,
        per_page=current_app.config['RAGTIME_COMMENTS_PER_PAGE'],
        error_out=False)
    comments = pagination.items
    prev = None
    if pagination.has_prev:
        prev = url_for('api.get_composition_comments', id=id, page=page-1)
    next = None
    if pagination.has_next:
        next = url_for('api.get_composition_comments', id=id, page=page+1)
    return jsonify({
        'comments': [comment.to_json() for comment in comments],
        'prev': prev,
        'next': next,
        'count': pagination.total
    })


@api.route('/compositions/<int:id>/comments/', methods=['POST'])
@permission_required(Permission.COMMENT)
def new_comment(id):
    composition = Composition.query.get_or_404(id)
    comment = Comment.from_json(request.json)
    comment.artist = g.current_user
    comment.composition = composition
    db.session.add(comment)
    db.session.commit()
    return jsonify(comment.to_json()), 201, \
        {'Location': url_for('api.get_comment', id=comment.id)}