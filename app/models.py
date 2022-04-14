import bleach
import hashlib
import re
from datetime import datetime
from flask import current_app, url_for
from flask_login import UserMixin, AnonymousUserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import TimedJSONWebSignatureSerializer as WebSerializer
from . import exceptions
from . import db
from . import login_manager
from .exceptions import ValidationError


class Permission:
    """
    Permission model for defining permissions of the app
        FOLLOW - User can follow other users
        REVIEW - User can write reviews for compositions
        PUBLISH - Uesr can publish compositions
        MODERATE - User can moderate reviews (edit, delete)
        ADMIN - User can do everything
    """
    FOLLOW = 1
    REVIEW = 2
    COMMENT = REVIEW
    PUBLISH = 4
    MODERATE = 8
    ADMIN = 16


class ReleaseType:
    """
    """
    SINGLE = 0
    EXTENDED_PLAY = 1
    ALBUM = 2


class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    default = db.Column(db.Boolean, default=False, index=True)
    users = db.relationship('User', backref='role', lazy='dynamic')
    # XXX: Why doesn't this set permissions to 0? default=0
    permissions = db.Column(db.Integer)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.permissions is None:
            self.permissions = 0

    @staticmethod
    def insert_roles():
        roles = {
            'User':             [Permission.FOLLOW, Permission.REVIEW, Permission.PUBLISH],
            'Moderator':        [Permission.FOLLOW, Permission.REVIEW, Permission.PUBLISH,
                                 Permission.MODERATE],
            'Administrator':    [Permission.FOLLOW, Permission.REVIEW, Permission.PUBLISH,
                                 Permission.MODERATE, Permission.ADMIN],
        }
        default_role = 'User'
        for r in roles:
            # see if role is already in table
            role = Role.query.filter_by(name=r).first()
            if role is None:
                # it's not so make a new one
                role = Role(name=r)
            role.reset_permissions()
            # add whichever permissions the role needs
            for perm in roles[r]:
                role.add_permission(perm)
            # if role is the default one, default is True
            role.default = (role.name == default_role)
            # add new role
            db.session.add(role)
        db.session.commit()

    def __repr__(self):
        return f'<Role {self.name}>'

    def add_permission(self, perm):
        if not self.has_permission(perm):
            self.permissions += perm

    def remove_permission(self, perm):
        if self.has_permission(perm):
            self.permissions -= perm

    def reset_permissions(self):
        self.permissions = 0

    def has_permission(self, perm):
        # Use bitwise AND to see if perm present
        return self.permissions & perm == perm


class Follow(db.Model):
    __tablename__ = 'follows'
    # Look! Same thing for these two
    follower_id = db.Column(db.Integer,
                            db.ForeignKey('users.id'),
                            primary_key=True)
    following_id = db.Column(db.Integer,
                             db.ForeignKey('users.id'),
                             primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    email = db.Column(db.String(64), unique=True, index=True)
    password_hash = db.Column(db.String(128))
    confirmed = db.Column(db.Boolean, default=False)
    # Artist info
    name = db.Column(db.String(64))
    location = db.Column(db.String(64))
    bio = db.Column(db.Text())
    last_seen = db.Column(db.DateTime(), default=datetime.utcnow)
    avatar_hash = db.Column(db.String(32))
    compositions = db.relationship('Composition', backref='artist', lazy='dynamic')
    # Followers and Following
    # NOTE: I'm *following* someone as a *follower*
    following = db.relationship('Follow',
                               foreign_keys=[Follow.follower_id],
                               backref=db.backref('follower', lazy='joined'),
                               lazy='dynamic',
                               cascade='all, delete-orphan')
    # NOTE: All the people that are *following* me are my *followers*
    followers = db.relationship('Follow',
                                foreign_keys=[Follow.following_id],
                                backref=db.backref('following', lazy='joined'),
                                lazy='dynamic',
                                cascade='all, delete-orphan')
    comments = db.relationship('Comment', backref='artist', lazy='dynamic')


    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # For the first time a user logs in, we'll set their role
        # The next time they log in they will skip this
        # TODO: Explain, how can we do this??? self.role hasn't been defined yet
        if self.role is None:
            # if the User has email that matches admin email, automatically
            # make that User an Administrator by giving them that role
            if self.email == current_app.config['RAGTIME_ADMIN']:
                self.role = Role.query.filter_by(name='Administrator').first()
            # otherwise, it's just a plain old user
            if self.role == None:
                self.role = Role.query.filter_by(default=True).first()

        if self.email is not None and self.avatar_hash is None:
            self.avatar_hash = self.email_hash()
        self.follow(self)

    def __repr__(self):
        return f'<User {self.username}>'

    @staticmethod
    def add_self_follows():
        for user in User.query.all():
            if not user.is_following(user):
                user.follow(user)
                db.session.add(user)
                db.session.commit()

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_confirmation_token(self, expiration_sec=3600):
        s = WebSerializer(current_app.secret_key, expiration_sec)
        return s.dumps({'confirm_id': self.id}).decode('utf-8')

    def confirm(self, token):
        s = WebSerializer(current_app.secret_key)
        try:
            data = s.loads(token.encode('utf-8'))
        except:
            return False
        # Matches the logged in user
        if data.get('confirm_id') != self.id:
            return False
        self.confirmed = True
        db.session.add(self)
        # Don't commit yet! We'll make sure it's legit when we go to the /commit page
        return True

    # Simple check for if a user can do something
    def can(self, perm):
        return self.role is not None and self.role.has_permission(perm)

    # Because it's very common to check for admin
    def is_administrator(self):
        return self.can(Permission.ADMIN)

    def ping(self):
        self.last_seen = datetime.utcnow()
        db.session.add(self)
        db.session.commit()

    # We use this to prevent
    def email_hash(self):
        return hashlib.md5(self.email.lower().encode('utf-8')).hexdigest()

    def unicornify(self, size=128):
        url = 'https://unicornify.pictures/avatar'
        hash = self.avatar_hash or self.email_hash()
        return f'{url}/{hash}?s={size}'

    def follow(self, user):
        if not self.is_following(user):
            f = Follow(follower=self, following=user)
            db.session.add(f)

    def unfollow(self, user):
        f = self.following.filter_by(following_id=user.id).first()
        if f:
            db.session.delete(f)

    def is_following(self, user):
        if user.id is None:
            return False
        return self.following.filter_by(
            following_id=user.id).first() is not None

    def is_a_follower(self, user):
        if user.id is None:
            return False
        return self.followers.filter_by(
            follower_id=user.id).first() is not None

    @property
    def followed_compositions(self):
        return Composition.query.join(Follow, Follow.following_id == Composition.artist_id)\
            .filter(Follow.follower_id == self.id)


    def generate_auth_token(self, expiration_sec):
        s = WebSerializer(current_app.config['SECRET_KEY'],
                          expires_in=expiration_sec)
        return s.dumps({'id': self.id}).decode('utf-8')


    @staticmethod
    def verify_auth_token(token):
        s = WebSerializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return None
        return User.query.get(data['id'])

    # Not identical to actual User model
    def to_json(self):
        json_user = {
            'url': url_for('api.get_user', id=self.id),
            'username': self.username,
            'last_seen': self.last_seen,
            'compositions_url': url_for('api.get_user_compositions', id=self.id),
            'followed_compositions_url': url_for('api.get_user_followed', id=self.id),
            'composition_count': self.compositions.count()
        }
        return json_user


class AnonymousUser(AnonymousUserMixin):
    def can(self, perm):
        return False

    def is_administrator(self):
        return False


class Composition(db.Model):
    """What our database holds"""
    __tablename__ = 'compositions'
    id = db.Column(db.Integer, primary_key=True)
    # 0 for single, 1 for ep, 2 for album
    release_type = db.Column(db.Integer)
    title = db.Column(db.String(64))
    description = db.Column(db.Text)
    description_html = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    artist_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    # TODO: what if we have a duplicate?
    slug = db.Column(db.String(128), unique=True)
    comments = db.relationship('Comment', backref='composition', lazy='dynamic')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


    @staticmethod
    def on_changed_description(target, value, oldvalue, initiator):
        allowed_tags = ['a']
        regex_str = r"@(\b[\w.]*\b)"
        matches = re.findall(regex_str, value, flags=re.M|re.I)
        for username in matches:
            # TODO some complicated regex stuff I need to explain
            user_link = url_for('main.user', username=username, _external=True)
            value = value.replace(f"@{username}", f'<a href="{user_link}">@{username}</a>')
        html = bleach.linkify(bleach.clean(value, tags=allowed_tags, strip=True))
        target.description_html = html

    def generate_slug(self):
        self.slug = f"{self.id}-" + re.sub(r'[^\w]+', '-', self.title.lower())
        db.session.add(self)
        db.session.commit()

    def to_json(self):
        json_composition = {
            'url': url_for('api.get_composition', id=self.id),
            'release_type': self.release_type,
            'title': self.title,
            'description': self.description,
            'description_html': self.description_html,
            'timestamp': self.timestamp,
            'artist_url': url_for('api.get_user', id=self.artist_id),
            'comments_url': url_for('api.get_composition_comments', id=self.id),
            'comment_count': self.comments.count()
        }
        return json_composition

    # deserializing
    @staticmethod
    def from_json(json_composition):
        release_type = json_composition.get('release_type')
        title = json_composition.get('title')
        description = json_composition.get('description')
        if release_type is None:
            raise ValidationError("Composition must have a release type")
        if title is None:
            raise ValidationError("Composition must have a title")
        if description is None:
            raise ValidationError("Composition must have a description")
        return Composition(release_type=release_type,
                           title=title,
                           description=description)


db.event.listen(Composition.description, 'set', Composition.on_changed_description)


class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    disabled = db.Column(db.Boolean, default=False)
    # TODO change to user?
    artist_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    composition_id = db.Column(db.Integer, db.ForeignKey('compositions.id'))

    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        allowed_tags = ['a']
        target.body_html = bleach.linkify(bleach.clean(
            value, tags=allowed_tags, strip=True))

    def to_json(self):
        json_comment = {
            'url': url_for('api.get_comment', id=self.id),
            'composition_url': url_for('api.get_composition', id=self.composition_id),
            'body': self.body,
            'body_html': self.body_html,
            'timestamp': self.timestamp,
            'artist_url': url_for('api.get_user', id=self.artist_id),
        }
        return json_comment

    # deserializing
    @staticmethod
    def from_json(json_comment):
        body = json_comment.get('body')
        if body is None or body == "":
            raise ValidationError("Comment must have a body")
        return Comment(body=body)


db.event.listen(Comment.body, 'set', Comment.on_changed_body)

login_manager.anonymous_user = AnonymousUser

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
