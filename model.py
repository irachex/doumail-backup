#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import logging
import random
import codecs
import simplejson as json

from google.appengine.ext import db


class Account(db.Model):
    uid = db.StringProperty()
    title = db.StringProperty()
    email = db.StringProperty()
    token_key = db.StringProperty(indexed=False)
    token_secret = db.StringProperty(indexed=False)
    
    def from_json(self, jsondata):
        data = json.loads(jsondata)
        self.uid = data["db:uid"]["$t"]
        self.title = data["title"]["$t"]
        
        
class Mail(db.Model):
    uid = db.StringProperty()
    name = db.StringProperty(indexed=False)
    id = db.StringProperty()
    title = db.StringProperty(indexed=False)
    content = db.TextProperty()
    author_name = db.StringProperty(indexed=False)
    author_id = db.StringProperty()
    time = db.StringProperty()
    unread = db.BooleanProperty(indexed=False)
    recv = db.BooleanProperty()

    def from_json(self, jsondata):
        return None
    