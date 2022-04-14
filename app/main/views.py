from flask import session, render_template, redirect, url_for, flash, current_app, request, abort, make_response
from flask_login import login_required, current_user
from . import main
from .forms import NameForm, EditProfileForm, EditProfileAdminForm, CompositionForm, CommentForm
from .. import db
from ..models import User, Role, Permission, Composition, Comment
from ..email import send_email
from ..decorators import admin_required, permission_required, log_visit


@main.route('/', methods=['GET', 'POST'])
@log_visit
def home():
    """How the page BEHAVES"""
    form = CompositionForm()
    if current_user.can(Permission.PUBLISH) and form.validate_on_submit():
        composition = Composition(release_type=form.release_type.data,
                                  title=form.title.data,
                                  description=form.description.data,
                                  # database needs a real User object
                                  artist=current_user._get_current_object())
        db.session.add(composition)
        db.session.commit()
        # must be generated after first commit
        composition.generate_slug()
        return redirect(url_for('.home'))
    # page number to render, from request's query string 'page',
    # with default of first page (1), and if type can't be int,
    # return default value
    page = request.args.get('page', 1, type=int)
    show_followed = False
    if current_user.is_authenticated:
        show_followed = bool(request.cookies.get('show_followed', ''))
    if show_followed:
        query = current_user.followed_compositions
    else:
        query = Composition.query
    # Which page of results do you want? We'll display <per_page> results, and won't
    # throw an error if you go outside how many pages we have!
    # NOTE: We may use a different query if show followed is true
    #pagination = Composition.query.order_by(Composition.timestamp.desc()).paginate(
    pagination = query.order_by(Composition.timestamp.desc()).paginate(
        page,
        per_page=current_app.config['RAGTIME_COMPS_PER_PAGE'],
        error_out=False)
    compositions = pagination.items
    # A ?page=2 will display in address when page selected is 2
    return render_template(
        'home.html',
        form=form,
        compositions=compositions,
        show_followed=show_followed,
        pagination=pagination
    )


@main.route('/user/<username>')
@log_visit
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    compositions = user.compositions.order_by(Composition.timestamp.desc()).all()
    return render_template('user.html', user=user, compositions=compositions)


@main.route('/composition/<slug>', methods=['GET', 'POST'])
@log_visit
def composition(slug):
    composition = Composition.query.filter_by(slug=slug).first_or_404()
    form = CommentForm()
    if form.validate_on_submit():
        comment = Comment(body=form.body.data,
                          composition=composition,
                          artist=current_user._get_current_object())
        db.session.add(comment)
        db.session.commit()
        flash('Comment submission successful.')
        return redirect(url_for('.composition', slug=composition.slug, page=-1))
    page = request.args.get('page', 1, type=int)
    if page == -1:
        # Calculate last page number
        page = (composition.comments.count() - 1) // \
               current_app.config['RAGTIME_COMMENTS_PER_PAGE'] + 1
    pagination = composition.comments.order_by(Comment.timestamp.asc()).paginate(
        page,
        per_page=current_app.config['RAGTIME_COMMENTS_PER_PAGE'],
        error_out=False)
    comments = pagination.items
    # Use list so we can pass to _compositions template
    return render_template('composition.html',
                           compositions=[composition],
                           form=form,
                           comments=comments,
                           pagination=pagination)


@main.route('/edit/<slug>', methods=["GET", "POST"])
@login_required
@log_visit
def edit_composition(slug):
    composition = Composition.query.filter_by(slug=slug).first_or_404()
    if current_user != composition.artist and \
            not current_user.can(Permission.ADMIN):
        abort(403)
    form = CompositionForm()
    if form.validate_on_submit():
        composition.release_type = form.release_type.data
        composition.title = form.title.data
        composition.description = form.description.data
        # regenerate in case the title changed
        composition.generate_slug()
        db.session.add(composition)
        db.session.commit()
        flash("Your composition was updated!")
        return redirect(url_for('.composition', slug=composition.slug))
    form.release_type.data = composition.release_type
    form.title.data = composition.title
    form.description.data = composition.description
    return render_template('edit_composition.html', form=form)


@main.route('/edit-profile', methods=['GET', 'POST'])
@login_required
@log_visit
def edit_profile():
    form = EditProfileForm()
    if form.validate_on_submit():
        # Change all user information and then save to database
        current_user.name = form.name.data
        current_user.location = form.location.data
        current_user.bio = form.bio.data
        db.session.add(current_user._get_current_object())
        db.session.commit()
        flash('Looking good! Your profile was updated.')
        return redirect(url_for('.user', username=current_user.username))
    # Show initial values so user can see what they have already
    form.name.data = current_user.name
    form.location.data = current_user.location
    form.bio.data = current_user.bio
    return render_template('edit_profile.html', form=form)


@main.route('/edit-profile-admin/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
@log_visit
def edit_profile_admin(id):
    user = User.query.get_or_404(id)
    form = EditProfileAdminForm(user=user)
    if form.validate_on_submit():
        user.email = form.email.data
        user.username = form.username.data
        user.confirmed = form.confirmed.data
        user.role = Role.query.get(form.role.data)
        user.name = form.name.data
        user.location = form.location.data
        user.bio = form.bio.data
        db.session.add(current_user._get_current_object())
        db.session.commit()
        flash('The profile was updated.')
        return redirect(url_for('.user', username=user.username))
    form.email.data = user.email
    form.username.data = user.username
    form.confirmed.data = user.confirmed
    # We must ensure role field gets int data
    form.role.data = user.role_id
    form.name.data = user.name
    form.location.data = user.location
    form.bio.data = user.bio
    return render_template('edit_profile.html', form=form, user=user)


@main.route('/follow/<username>')
@login_required
@permission_required(Permission.FOLLOW)
@log_visit
def follow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash("That is not a valid user.")
        return redirect(url_for('.home'))
    if current_user.is_following(user):
        flash("Looks like you are already following that user.")
        return redirect(url_for('.user', username=username))
    current_user.follow(user)
    db.session.commit()
    flash(f"You are now following {username}")
    return redirect(url_for('.user', username=username))


# NOTE: This should be done by student
@main.route('/unfollow/<username>')
@login_required
@permission_required(Permission.FOLLOW)
@log_visit
def unfollow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash("That is not a valid user.")
        return redirect(url_for('.home'))
    if not current_user.is_following(user):
        flash("Looks like you never followed that user in the first place.")
        return redirect(url_for('.user', username=username))
    current_user.unfollow(user)
    db.session.commit()
    flash(f"You unfollowed {username}")
    return redirect(url_for('.user', username=username))


# Who my followers are
@main.route('/followers/<username>')
@log_visit
def followers(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash("That is not a valid user.")
        return redirect(url_for('.home'))
    page = request.args.get('page', 1, type=int)
    pagination = user.followers.paginate(
        page,
        per_page=current_app.config['RAGTIME_FOLLOWERS_PER_PAGE'],
        error_out=False)
    # convert to only follower and timestamp
    follows = [{'user': item.follower, 'timestamp': item.timestamp}
               for item in pagination.items]
    return render_template('followers.html',
                           user=user,
                           title="Followers of",
                           endpoint='.followers',
                           pagination=pagination,
                           follows=follows)


# Who I'm following
# NOTE: Done by student
@main.route('/following/<username>')
@log_visit
def following(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash("That is not a valid user.")
        return redirect(url_for('.home'))
    page = request.args.get('page', 1, type=int)
    pagination = user.following.paginate(
        page,
        per_page=current_app.config['RAGTIME_FOLLOWING_PER_PAGE'],
        error_out=False)
    # convert to only following and timestamp
    following = [{'user': item.following, 'timestamp': item.timestamp}
               for item in pagination.items]
    return render_template('followers.html',
                           user=user,
                           title="Followed by",
                           endpoint='.followers',
                           pagination=pagination,
                           follows=following)


@main.route('/all')
@login_required
@log_visit
def show_all():
    resp = make_response(redirect(url_for('.home')))
    resp.set_cookie('show_followed', '', max_age=30*24*60*60) # 30 days
    return resp


@main.route('/followed')
@login_required
@log_visit
def show_followed():
    resp = make_response(redirect(url_for('.home')))
    resp.set_cookie('show_followed', '1', max_age=30*24*60*60) # 30 days
    return resp


@main.route('/moderate')
@login_required
@permission_required(Permission.MODERATE)
@log_visit
def moderate():
    page = request.args.get('page', 1, type=int)
    pagination = Comment.query.order_by(Comment.timestamp.desc()).paginate(
        page,
        per_page=current_app.config['RAGTIME_COMMENTS_PER_PAGE'],
        error_out=False)
    comments = pagination.items
    return render_template('moderate.html',
                           comments=comments,
                           pagination=pagination,
                           page=page)


@main.route('/moderate/enable/<int:id>')
@login_required
@permission_required(Permission.MODERATE)
@log_visit
def moderate_enable(id):
    comment = Comment.query.get_or_404(id)
    comment.disable = False
    db.session.add(comment)
    return redirect(url_for('.moderate',
                            page=request.args.get('page', 1, type=int)))


@main.route('/moderate/disable/<int:id>')
@login_required
@permission_required(Permission.MODERATE)
@log_visit
def moderate_disable(id):
    comment = Comment.query.get_or_404(id)
    comment.disable = True
    db.session.add(comment)
    return redirect(url_for('.moderate',
                            page=request.args.get('page', 1, type=int)))
