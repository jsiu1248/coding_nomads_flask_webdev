"""
USE ONLY FOR DEVELOPMENT!
"""

import sys
from app import fake, db, create_app
from app.models import User
from flask import Flask

if __name__ == "__main__":
    # be sure to install packages (requirements/dev.txt) and
    # set environment variables or create launch files
    # and also create migrations folder via flask db init
    app: Flask = create_app('development')
    with app.app_context():
        db.create_all()
        if User.query.count() < 20:
            fake.create_fake_data()
        print(f"You can use this to login:\nEmail: {User.query.first().email}\nPassword: password")
