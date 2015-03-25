"""Main application module."""
import json
import logging
import os

from google.appengine.api import images
from google.appengine.api import memcache
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
          request_handler.abort(403)

        request_handler.user_id = request_handler.user.user_id()
        action(request_handler, *args, **kwargs)
    return authenticated


def get_user_profile(user_id):
  profile_key = ndb.Key('Profile', user_id)
  # Get the profile from memcache, then the datastore, or create
  profile = memcache.get(profile_key.urlsafe())
  if not profile:
    profile = profile_key.get()
    memcache.set(profile_key.urlsafe(), profile)
  if not profile:
    profile = models.Profile(key=profile_key)
    profile.put()
    memcache.set(profile_key.urlsafe(), profile)

  return profile

#------------------------ Exceptions ------------------------------------------


class EntityNotFoundException(Exception):

    def __init__(self, kind, entity_id):
        self.kind = kind
        self.entity_id = entity_id

    def __str__(self):
      return '{} with id={} does not navbar-rightexist!'.format(self.kind,
                                                                self.entity_id)


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


class ProfileHandler(BaseHandler):

    """Profile request handler."""
    @login_required
    def get(self):
        profile = ndb.Key('Profile', self.user_id).get()
        if profile and profile.avatar:
          profile.avatar = '/uploads/' + profile.key.urlsafe() + '.png'
        return_json(self.response, profile, models.NdbModelEncoder())

    @login_required
    def post(self):
        profile_key = ndb.Key('Profile', self.user_id)
        profile = profile_key.get()
        if not profile:
            profile = models.Profile(key=profile_key)

        profile.avatar = images.resize(self.request.get('avatar'), 72, 72)
        profile.put()
        profile.avatar = '/uploads/' + profile.key.urlsafe() + '.png'
        return_json(self.response, profile, models.NdbModelEncoder())


class TopicsHandler(BaseHandler):

    """Profile request handler."""

    def get(self):
        # Get the user's profile and store in memcache
        query = models.Topic.query().order(-models.Topic.created)
        response = {
            'topics': [],
            'can_vote': False,
            'my_topics': {},
            'my_votes': {}
        }
        for t in query.fetch(1000):
            if t.image:
              t.image = '/uploads/' + t.key.urlsafe() + '.png'
            response['topics'].append(t)

        user = users.get_current_user()
        if user:
          profile = get_user_profile(user.user_id())
          response['can_vote'] = True
          response['my_topics'] = {t.id(): True for t in profile.topics}
          response['my_votes'] = {v.topic.id(): v.vote for v in profile.votes}

        return_json(self.response, response, models.NdbModelEncoder())

    @login_required
    def put(self, id, vote):
        topic = ndb.Key('Topic', int(id)).get()
        if not topic:
          self.abort(404)

        if vote == 'up':
            topic.up_votes += 1
        elif vote == 'down':
            topic.down_votes += 1
        topic.put()
        if topic and topic.image:
          topic.image = '/uploads/' + topic.key.urlsafe() + '.png'

        # Update profile
        profile = get_user_profile(self.user_id)
        profile.votes.append(models.Vote(topic=topic.key, vote=vote))
        profile.put()
        memcache.set(profile.key.urlsafe(), profile)
        response = {
            'topic': topic,
            'my_votes': {v.topic.id(): v.vote for v in profile.votes}
        }
        return_json(self.response, response, models.NdbModelEncoder())

    @login_required
    def post(self):
        profile = get_user_profile(self.user_id)
        topic = models.Topic(name=self.request.get('name'))
        if self.request.get('tags'):
            topic.tags = self.request.get('tags').split(',')
        if self.request.get('image'):
            topic.image = images.resize(self.request.get('image'), 400)

        topic_key = topic.put()
        profile.topics.append(topic_key)
        profile.put()
        memcache.set(profile.key.urlsafe(), profile)
        if topic and topic.image:
          topic.image = '/uploads/' + topic.key.urlsafe() + '.png'
        return_json(self.response, topic, models.NdbModelEncoder())


class ImageHandler(BaseHandler):

    def get(self, urlsafe_key):
        entity = ndb.Key(urlsafe=urlsafe_key[:-4]).get()
        if not entity:
            self.abort(404)
        self.response.headers['Content-Type'] = 'image/png'
        if entity.key.kind() == 'Topic':
          self.response.out.write(entity.image)
        elif entity.key.kind() == 'Profile':
          self.response.out.write(entity.avatar)


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
    ('/profile', ProfileHandler),
    ('/topics', TopicsHandler),
    ('/topics/(.+)/(up|down)', TopicsHandler),
    ('/uploads/(.+)', ImageHandler)
], debug=os.environ['SERVER_SOFTWARE'].startswith('Development'))
