#!/usr/bin/env python

from typing import Optional, List, Dict

import argparse
import logging
import os
import uuid

import flask
import flask_restful
import flask_sqlalchemy

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


def main() -> None:
    """Application entry point."""

    args = parse_args()

    if args.database_path.startswith('/'):
        database_path = args.database_path
    else:
        database_path = os.path.join(os.getcwd(), args.database_path)

    app = flask.Flask(__name__, template_folder='templates')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{database_path}'
    db = flask_sqlalchemy.SQLAlchemy(app)

    class Article(db.Model):

        __tablename__ = 'articles'

        index = db.Column(db.Integer, primary_key=True)
        article_id = db.Column(db.String)
        word_count = db.Column(db.Integer)
        title = db.Column(db.String)
        content = db.Column(db.String)
        next_article_id = db.Column(db.String)

        @staticmethod
        def get_next(username: str) -> Optional['Article']:
            """Return the next unread article by a given user."""

            user = User.query.filter_by(username=username).first()

            if user is None:
                return None

            if user.last_article_id is None:
                article = Article.query.first()
                if article is None:
                    return None

                user.last_article_id = article.article_id
                db.session.commit()

                return article
            else:
                last_article = Article.query.filter_by(article_id=user.last_article_id).first()
                if last_article is None:
                    return None
                next_article = Article.query.filter_by(article_id=last_article.next_article_id).first()
                if next_article is None:
                    user.last_article_id = None  # wraps around already read articles
                    db.session.commit()
                    return None
                else:
                    user.last_article_id = next_article.article_id
                    db.session.commit()
                    return next_article

        @staticmethod
        def find_by_keyword(keyword: str) -> List['Article']:
            """Return a list of articles containing the given word (case insensitive)."""
            query = '''\
                SELECT *
                FROM articles
                WHERE article_id IN (
                    SELECT article_id
                    FROM tokens
                    WHERE token = ?
                )'''
            result = db.engine.execute(query, (keyword.strip().lower(),))
            return result.fetchall()

    class User(db.Model):

        __tablename__ = 'users'

        username = db.Column(db.String, primary_key=True)
        token = db.Column(db.String, unique=True, nullable=True)
        last_article_id = db.Column(db.String, unique=False, nullable=True)

        @staticmethod
        def get_authenticated() -> Optional['User']:
            """Return User instance or None."""
            if 'token' in flask.request.cookies:
                token = flask.request.cookies['token']
                return User.query.filter_by(token=token).first()

        @staticmethod
        def is_authenticated() -> bool:
            """Return True if the current user is authenticated."""
            return User.get_authenticated() is not None

        @staticmethod
        def authenticate(username: str) -> str:
            """Return new or existing token for a given username."""

            user = User.query.filter_by(username=username).first()

            if user is None:
                user = User(username=username, token=uuid.uuid4().hex)
                db.session.add(user)
                db.session.commit()
                logger.info('Created and authenticated new user: "%s"', username)
            else:
                if user.token is None:
                    user.token = uuid.uuid4().hex
                    db.session.commit()
                    logger.info('Authenticated existing user: "%s"', username)
                else:
                    logger.info('User already authenticated: "%s"', username)

            return user.token

        @staticmethod
        def unauthenticate(username: str) -> None:
            """Remove the corresponding token from the database."""

            user = User.query.filter_by(username=username).first()

            if user is None:
                logger.warning('Username not found: "%s"', username)
            else:
                if user.token is None:
                    logger.info('User was not authenticated: "%s"', username)
                else:
                    user.token = None
                    db.session.commit()
                    logger.info('User no longer authenticated: "%s"', username)

    db.create_all()

    def authenticated(method):
        """Return a decorator for securing endpoints with a token."""
        def wrapper(*args, **kwargs):
            if User.is_authenticated():
                return method(*args, **kwargs)
            return flask.redirect('/login')
        return wrapper

    @app.route('/')
    @authenticated
    def index():
        """Return the index page."""
        return flask.render_template('index.html')

    @app.route('/logout')
    def logout():
        """Return the login page."""
        user = User.get_authenticated()
        if user is not None:
            User.unauthenticate(user.username)
        return flask.redirect('/login')

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        """Return the login page or handle HTML form."""
        if flask.request.method == 'GET':
            if User.is_authenticated():
                return flask.redirect('/')
            return flask.render_template('login.html')
        elif flask.request.method == 'POST':
            return handle_login(flask.request.form)

    def handle_login(form: Dict) -> None:
        """Set cookie based on username from the login form."""

        if 'username' not in form:
            return flask.abort(400)

        username = form['username'].strip()

        if username:
            token = User.authenticate(username)
            response = flask.make_response(flask.redirect('/'))
            response.set_cookie('token', token)
            return response
        else:
            return flask.abort(400)

    api = flask_restful.Api(app)

    def serialize(article: Dict) -> Dict:
        """Return an article to be serialized as JSON."""
        return {
            'id': article.article_id,
            'word_count': article.word_count,
            'title': article.title,
            'content': article.content
        }

    class RESTArticle(flask_restful.Resource):

        @authenticated
        def get(self, article_id: str) -> Optional[Dict]:
            """Return a serialized Article or None."""
            article = Article.query.filter_by(article_id=article_id).first()
            if article is None:
                flask.abort(404)
            else:
                return serialize(article)

    class RESTArticlesByWord(flask_restful.Resource):

        PARAMETER_NAME = 'keyword'

        @authenticated
        def get(self) -> Optional[Dict]:
            """Return a collection of serialized Articles."""
            request_params = flask_restful.request.args

            if self.PARAMETER_NAME not in request_params:
                logger.error('Bad request due to missing "%s" query parameter', self.PARAMETER_NAME)
                flask.abort(400)
            else:
                keyword = request_params[self.PARAMETER_NAME]
                articles = Article.find_by_keyword(keyword)
                return {
                    'num_articles': len(articles),
                    'articles': list(map(serialize, articles))
                }

    class RESTNextArticle(flask_restful.Resource):

        @authenticated
        def get(self) -> Optional[Dict]:
            """Return a serialized Article or None."""
            user = User.get_authenticated()
            if user is not None:
                article = Article.get_next(user.username)
                if article is None:
                    flask.abort(404)
                else:
                    return serialize(article)

    api.add_resource(RESTArticle, '/articles/<article_id>')
    api.add_resource(RESTArticlesByWord, '/articles')
    api.add_resource(RESTNextArticle, '/next-article')

    app.run(port=args.port, debug=False)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument('database_path', help='path to SQL database file')
    parser.add_argument('-p', '--port', type=int, default=8080)
    return parser.parse_args()


if __name__ == '__main__':
    main()
