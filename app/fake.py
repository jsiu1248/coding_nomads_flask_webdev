from random import randint
from sqlalchemy.exc import IntegrityError
from faker import Faker
from . import db
from .models import User, Composition, Comment

def create_fake_data():
    users()
    compositions()
    comments()

def users(count=20):
    fake = Faker()
    i = 0
    while i < count:
        u = User(email=fake.email(),
                 username=fake.user_name(),
                 password='password',
                 confirmed=True,
                 name=fake.name(),
                 location=fake.city(),
                 bio=fake.text(),
                 last_seen=fake.past_date())
        db.session.add(u)
        try:
            db.session.commit()
            i += 1
        except IntegrityError:
            # An unlikely event that might happen if email or username is duplicated
            # in this case, the data added previously is rolled back (removed)
            db.session.rollback()


def compositions(count=200):
    fake = Faker()
    user_count = User.query.count()
    for i in range(count):
        # assign random user to each composition using offset()
        # which discards X number of results, then first() gives first of remaining
        u = User.query.offset(randint(0, user_count - 1)).first()
        c = Composition(release_type=randint(0,2),
                        title=fake.bs(),
                        description=fake.text(),
                        timestamp=fake.past_date(),
                        artist=u)
        db.session.add(c)
    db.session.commit()
    for c in Composition.query.all():
        c.generate_slug()


def comments(count=1000):
    fake = Faker()
    composition_count = Composition.query.count()
    user_count = User.query.count()
    for i in range(count):
        u = User.query.offset(randint(0, user_count - 1)).first()
        c = Composition.query.offset(randint(0, composition_count - 1)).first()
        comment = Comment(body=fake.text(),
                          timestamp=fake.past_date(),
                          artist=u,
                          composition=c)
        db.session.add(c)
    db.session.commit()
