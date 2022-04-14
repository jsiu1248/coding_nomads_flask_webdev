from flask import url_for
from base64 import b64encode
from app.models import Role, User, Permission, Follow, Comment, Composition
from app import db
from datetime import datetime
import json

def get_api_headers(username, password):
    return {
        'Authorization':
            'Basic ' + b64encode(
                (username + ':' + password).encode('utf-8')).decode('utf-8'),
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }

class TestAPI():
    def test_404(self, new_app):
        response = new_app.get(
            '/wrong/url',
            headers=get_api_headers('email', 'password'))
        assert response.status_code == 404
        json_response = json.loads(response.get_data(as_text=True))
        assert json_response['error'] == 'not found'

    def test_no_auth(self, new_app):
        print(url_for('api.get_compositions'))
        response = new_app.get(url_for('api.get_compositions'),
                               content_type='application/json')
        assert response.status_code == 401

    def test_compositions(self, new_app, roles):
        # add user
        r = Role.query.filter_by(name='User').first()
        assert r is not None
        u = User(email='john@example.com', username='john', password='cat', confirmed=True, role=r)
        assert u.can(Permission.PUBLISH)
        db.session.add(u)
        db.session.commit()

        # write comp
        response = new_app.post(
            '/api/v1/compositions/',
            headers=get_api_headers('john@example.com', 'cat'),
            data=json.dumps({'description': 'description of the www.blog.com composition', 'title': 'man', 'release_type': 1}))
        assert response.status_code == 201
        url = response.headers.get('Location')
        assert url is not None

        # get new comp
        response = new_app.get(
            url,
            headers=get_api_headers('john@example.com', 'cat'))
        assert response.status_code == 200
        json_response = json.loads(response.get_data(as_text=True))
        assert 'http://localhost:5000' + json_response['url'] == url
        assert json_response['description'] == 'description of the www.blog.com composition'
        assert json_response['description_html'] == 'description of the <a href="http://www.blog.com" rel="nofollow">www.blog.com</a> composition'
        assert json_response['title'] == 'man'
        assert json_response['release_type'] == 1

        response = new_app.put(
            f'/api/v1/compositions/1',
            headers=get_api_headers('john@example.com', 'cat'),
            json=json.dumps({'description': 'this is my dog'})
        )
        assert response.status_code == 200

        response = new_app.get(
            url,
            headers=get_api_headers('john@example.com', 'cat'))
        assert response.status_code == 200
        json_response = json.loads(response.get_data(as_text=True))
        assert 'http://localhost:5000' + json_response['url'] == url
        assert json_response['description'] == 'this is my dog'


    def test_comments(self, new_app, roles):
        u = User.query.first()
        assert u.can(Permission.COMMENT)
        c = Composition(description="this is my dog meant for the put up a fight",
                        title="u wot m8",
                        release_type=1,
                        timestamp=datetime.utcnow(),
                        artist=u)
        db.session.add(u)
        db.session.add(c)
        db.session.commit()

        response = new_app.post(
            '/api/v1/compositions/1/comments/',
            headers=get_api_headers('john@example.com', 'cat'),
            data=json.dumps({'body': 'let''s talk about pickles shall we'}))
        assert response.status_code == 201
        url = response.headers.get('Location')
        assert url is not None

        response = new_app.get(
            url,
            headers=get_api_headers('john@example.com', 'cat'))
        assert response.status_code == 200
        json_response = json.loads(response.get_data(as_text=True))
        assert 'http://localhost:5000' + json_response['url'] == url
        assert json_response['body'] == 'let''s talk about pickles shall we'
        assert json_response['body_html'] == 'let''s talk about pickles shall we'


    def test_user(self, new_app, roles):
        response = new_app.get(
            '/api/v1/users/1',
            headers=get_api_headers('john@example.com', 'cat'))
        assert response.status_code == 200
        json_response = json.loads(response.get_data(as_text=True))
        assert json_response['username'] == User.query.first().username
        assert json_response['composition_count'] == 2
        url = '/api/v1/users/1/compositions/'
        assert url in json_response['compositions_url']
        followed_comps = json_response['followed_compositions_url']


        # get their comps
        response = new_app.get(
            url,
            headers=get_api_headers('john@example.com', 'cat'))
        assert response.status_code == 200
        json_response = json.loads(response.get_data(as_text=True))
        assert json_response['compositions'][1]['title'] == 'man'
        assert json_response['compositions'][0]['title'] == 'u wot m8'
        assert json_response['count'] == 2

        new = User(username="perse", password="stuff", email="ttt@example.com")
        u = User.query.first()
        u.follow(new)
        c = Composition(description="this is my dog meant for the put up a fight",
                        title="target",
                        release_type=1,
                        timestamp=datetime.utcnow(),
                        artist=new)
        response = new_app.get(
            followed_comps,
            headers=get_api_headers('john@example.com', 'cat'))
        assert response.status_code == 200
        json_response = json.loads(response.get_data(as_text=True))
        assert json_response['compositions'][0]['title'] == 'target'
        assert json_response['count'] == 3



