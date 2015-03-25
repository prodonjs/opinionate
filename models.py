'''Datastore Models
Created on Mar 24, 2015

@author: prodonjs
'''
import calendar
import json
import re
import time

from google.appengine.api import memcache
from google.appengine.ext import ndb


#------------------------ Module variables and functions-----------------------
RE_URL_UNSAFE = re.compile(r'[^a-zA-Z0-9_\-.]+')


def make_url_safe(value, substitute):
    """Replaces unsafe URL characters with the provided substitute."""
    return RE_URL_UNSAFE.sub(substitute, value).lower().strip(' ' + substitute)


class NdbModelEncoder(json.JSONEncoder):

    def default(self, o):
        """Override default encoding for Model and Key objects."""
        if isinstance(o, ndb.Model):
            obj_dict = o.to_dict()
            obj_dict['id'] = o.key.id()
            return obj_dict
        elif isinstance(o, ndb.Key):
            return {'kind': o.kind(), 'id': o.id()}
        else:
            return super(NdbModelEncoder, self).default(o)


class TimestampedModel(ndb.Model):

    created = ndb.IntegerProperty(indexed=True)
    modified = ndb.IntegerProperty()

    def _pre_put_hook(self):
        """Pre-put operations."""
        now = calendar.timegm(time.gmtime())
        self.modified = now
        if not self.created:
            self.created = now


class Topic(TimestampedModel):

    """Topic that can be voted on."""
    name = ndb.StringProperty(required=True)
    image = ndb.BlobProperty()
    tags = ndb.StringProperty(repeated=True)
    up_votes = ndb.IntegerProperty(required=True, default=0)
    down_votes = ndb.IntegerProperty(required=True, default=0)


class Vote(TimestampedModel):

    """User's vote on a particular Topic."""
    topic = ndb.KeyProperty(Topic, required=True)
    vote = ndb.IntegerProperty(required=True, choices=(-1, 1))


class Profile(TimestampedModel):

    """User profile."""
    avatar = ndb.BlobProperty()
    topics = ndb.KeyProperty(Topic, repeated=True)
    votes = ndb.StructuredProperty(Vote, repeated=True)
