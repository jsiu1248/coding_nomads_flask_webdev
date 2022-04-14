import pytest
from flask import current_app
from flask_login import current_user
from app import create_app, db
from app.models import User, Role, Permission
from app.email import send_email

class TestFlaskApp():
    def test_tfa001_uno(self):
        assert True

    def test_tfa002_app_creation(self):
        self.app = create_app('testing')
        assert self.app

    def test_tfa003_current_app(self):
        app = create_app('testing')
        with app.app_context():
            # current_app now defined (or should be)
            assert current_app

    def test_tfa004_current_app2(self):
        app = create_app('testing')
        app.app_context().push()
        # current_app now defined (or should be)
        assert current_app
        assert current_app.config['TESTING']


class TestUserAuth():

    def test_tua001_add_user(self, new_app):
        u = User(email='john@example.com', username='john', password='cat')
        db.session.add(u)
        db.session.commit()

    def test_tua002_test_has_hash(self, new_app):
        u = User.query.first()
        assert u.password_hash is not None

    def test_tua003_test_login(self, new_app):
        u = User.query.first()
        assert not u.verify_password('catcat')
        assert u.verify_password('cat')

    def test_tua004_getter_throws(self, new_app):
        u = User.query.first()
        try:
            u.password
            assert False
        except AttributeError:
            pass # passes test if here
        except:
            assert False

    def test_tua005_salt_is_random(self, new_app):
        u1 = User(password="cat")
        u2 = User(password="cat")
        assert u1.password_hash != u2.password_hash

    def test_tua005_token_valid(self, new_app):
        u = User.query.first()
        token = u.generate_confirmation_token()
        assert u.confirm(token)


class TestUserRoles():

    def test_tur001_perm_funcs(self):
        r = Role(name='User')
        # add two perms
        r.add_permission(Permission.FOLLOW)
        r.add_permission(Permission.REVIEW)
        # assert has one of those
        assert r.has_permission(Permission.FOLLOW)
        # assert it doesn't have another
        assert not r.has_permission(Permission.PUBLISH)
        r.remove_permission(Permission.FOLLOW)
        # assert now it doesn't have removed one
        assert not r.has_permission(Permission.FOLLOW)
        # erase all perms
        r.reset_permissions()
        assert not r.has_permission(Permission.REVIEW)

    def test_tur002_insert_roles_names(self):
        Role.insert_roles()
        roles = Role.query.all()
        names = [role.name for role in roles]
        assert ('User' and 'Administrator' and 'Moderator') in names
        # other stuff

    def test_tur003_user_perms(self):
        Role.insert_roles()
        u = Role.query.filter_by(name='User').first()
        assert u.has_permission(Permission.FOLLOW)
        assert u.has_permission(Permission.REVIEW)
        assert u.has_permission(Permission.PUBLISH)
        assert not u.has_permission(Permission.MODERATE)

    def test_tur004_mod_perms(self):
        Role.insert_roles()
        m = Role.query.filter_by(name='Moderator').first()
        assert m.has_permission(Permission.MODERATE)
        assert not m.has_permission(Permission.ADMIN)

    def test_tur005_admin_perms(self):
        Role.insert_roles()
        a = Role.query.filter_by(name='Administrator').first()
        assert a.has_permission(Permission.ADMIN)

    def test_tur006_new_user_perms(self):
        Role.insert_roles()
        u = User(name='john', password='cat', email='john@johnnyboy.com', confirmed=True)
        assert u.can(Permission.FOLLOW)
        assert u.can(Permission.REVIEW)
        assert u.can(Permission.PUBLISH)
        assert not u.can(Permission.MODERATE)
        assert not u.can(Permission.ADMIN)
        assert u.role.default
        assert u.role.name == 'User'
