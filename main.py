"""Main application module."""
import json
import logging
import os

from google.appengine.api import images
from google.appengine.api import users
from google.appengine.ext import ndb
import jinja2
import webapp2

import models
# Configure jinja
TEMPLATES_LOADER = jinja2.FileSystemLoader([
    os.path.dirname(__file__),
    os.path.join(os.path.dirname(__file__), 'templates')
])
JINJA_ENVIRONMENT = jinja2.Environment(
    loader=TEMPLATES_LOADER,
    extensions=['jinja2.ext.autoescape'],
    variable_start_string='[[',
    variable_end_string=']]',
    autoescape=True)

#------------------------ Module functions ------------------------------------


def return_json(response, data, encoder=None):
    """Creates a JSON response from in the request handler.

    Params:
      response: webapp2.Response
      data: Any JSON-encodable data type
      encoder: (Optional) a custom JSONEncoder object
    """
    response.headers['Content-Type'] = 'application/json'
    if encoder:
        response.write(encoder.encode(data))
    else:
        response.write(json.dumps(data))


def login_required(action):
    """Action decorator to ensure the user is authenticated."""
    def authenticated(request_handler, *args, **kwargs):
        request_handler.user = users.get_current_user()
        if not request_handler.user:
            request_handler.redirect(
                users.create_login_url(request_handler.request.uri))
        else:
            request_handler.username = request_handler.user.nickname()
            if '@' in request_handler.username:
                end = request_handler.username.index('@')
                request_handler.username = request_handler.username[0:end]
            action(request_handler, *args, **kwargs)
    return authenticated

#------------------------ Exceptions ------------------------------------------


class EntityNotFoundException(Exception):

    def __init__(self, kind, entity_id):
        self.kind = kind
        self.entity_id = entity_id

    def __str__(self):
        return '{} with id={} does not navbar-rightexist!'.format(self.kind, self.entity_id)


class EntityExistsException(Exception):

    def __init__(self, kind, entity_id):
        self.kind = kind
        self.entity_id = entity_id

    def __str__(self):
        return '{} with id={} already exists!'.format(self.kind, self.entity_id)


#------------------------ Request handlers ------------------------------------


class BaseHandler(webapp2.RequestHandler):

    def handle_exception(self, exception, debug):
        # Log the error.
        logging.exception(exception)

        # If the exception is a HTTPException, use its error code.
        # Otherwise use a generic 500 error code.
        if isinstance(exception, webapp2.HTTPException):
            self.response.set_status(exception.code)
        else:
            self.response.set_status(500)

        # Return JSON
        self.response.headers['Content-Type'] = 'application/json'
        self.response.write(json.dumps(
            {'error': True, 'errorMessage': str(exception)}
        ))


class AvatarHandler(BaseHandler):

    def get(self, id):
        profile = ndb.Key(urlsafe=id[:-4]).get()
        if not profile:
            self.abort(404)
        self.response.headers['Content-Type'] = 'image/png'
        self.response.out.write(profile.avatar)


class ProfileHandler(BaseHandler):

    """Profile request handler."""

    def get(self):
        user = users.get_current_user()
        if not user:
            self.abort(403)
        profile = ndb.Key('Profile', user.user_id()).get()
        if profile and profile.avatar:
            profile.avatar = '/avatar/' + profile.key.urlsafe() + '.png'
        return_json(self.response, profile, models.NdbModelEncoder())

    def post(self):
        user = users.get_current_user()
        if not user:
            self.abort(403)
        profile_key = ndb.Key('Profile', user.user_id())
        profile = profile_key.get()
        if not profile:
            profile = models.Profile(key=profile_key)

        profile.avatar = images.resize(self.request.get('avatar'), 72, 72)
        profile.put()
        profile.avatar = '/avatar/' + profile.key.urlsafe() + '.png'
        return_json(self.response, profile, models.NdbModelEncoder())


class TopicsHandler(BaseHandler):

    """Profile request handler."""

    def get(self):
        query = models.Topic.query().order(-models.Topic.created)
        topics = []
        for t in query:
            if t.image:
                t.image = '/topics/image/' + t.key.urlsafe() + '.png'
            topics.append(t)
        return_json(self.response, topics, models.NdbModelEncoder())

    def put(self, id, vote):
        user = users.get_current_user()
        topic = ndb.Key('Topic', id).get()
        if not topic or not user:
            self.abort(403)

        if vote == 'up':
            topic.up_votes += 1
        elif vote == 'down':
            topic.down_votes += 1
        topic.put()
        if topic and topic.image:
            topic.image = '/topics/image/' + topic.key.urlsafe() + '.png'
        return_json(self.response, topic, models.NdbModelEncoder())

    def post(self):
        user = users.get_current_user()
        if not user:
            self.abort(403)

        topic = models.Topic(name=self.request.get('name'))
        if self.request.get('tags'):
            topic.tags = self.request.get('tags').split(',')
        if self.request.get('image'):
            topic.image = images.resize(self.request.get('image'), 400)

        topic.put()
        if topic and topic.image:
            topic.image = '/topics/image/' + topic.key.urlsafe() + '.png'
        return_json(self.response, topic, models.NdbModelEncoder())


class TopicsImageHandler(BaseHandler):

    def get(self, id):
        topic = ndb.Key(urlsafe=id[:-4]).get()
        if not topic:
            self.abort(404)
        self.response.headers['Content-Type'] = 'image/png'
        self.response.out.write(topic.image)


class IndexHandler(BaseHandler):

    """Index page request handler."""

    def get(self):
        user = users.get_current_user()
        view_vars = {
            'username': '',
            'login': ''
        }
        if user:
            view_vars['username'] = user.nickname()
        else:
            view_vars['login'] = users.create_login_url()
        template = JINJA_ENVIRONMENT.get_template('index.html')
        self.response.write(template.render(view_vars))


application = webapp2.WSGIApplication([
    ('/', IndexHandler),
    ('/avatar/(.+)', AvatarHandler),
    ('/profile', ProfileHandler),
    ('/topics', TopicsHandler),
    ('/topics/(.+)/(up|down)', TopicsHandler),
    ('/topics/image/(.+)', TopicsImageHandler)
], debug=os.environ['SERVER_SOFTWARE'].startswith('Development'))
