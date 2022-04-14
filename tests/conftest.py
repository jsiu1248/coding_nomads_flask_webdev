import pytest
from app import create_app, db
from app.models import Role

print("LOADING CONFTEST")

@pytest.fixture(scope='session')
def pony():
    """My Little Pony"""
    pass

@pytest.fixture(scope='module')
def new_app():
    """ My fixture """
    # setup
    app = create_app('testing')
    assert 'data-test.sqlite' in app.config['SQLALCHEMY_DATABASE_URI']
    test_client = app.test_client()
    ctx = app.app_context()
    ctx.push()
    db.create_all()

    # testing begins
    yield test_client

    # teardown
    db.session.remove()
    db.drop_all()
    ctx.pop()

@pytest.fixture(scope='function')
def roles():
    Role.insert_roles()
    yield
