import os
from app import create_app, db, mail
from app.models import User, Role, Permission, Composition, Follow, Comment
from flask_migrate import Migrate, upgrade

app = create_app(os.getenv('FLASK_CONFIG') or 'default')
migrate = Migrate(app, db)

@app.shell_context_processor
def make_shell_context():
    return dict(db=db,
                mail=mail,
                User=User,
                Role=Role,
                Permission=Permission,
                Composition=Composition,
                Follow=Follow,
                Comment=Comment,)


@app.cli.command()
def deploy():
    """ Run deployment tasks """

    # migrate database
    upgrade()

    Role.insert_roles()

    User.add_self_follows()
