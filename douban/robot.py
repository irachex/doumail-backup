#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import logging
import codecs
import urllib
try:
    import simplejson as json
except:
    import json

from client import DoubanOAuth
from model import Account, Mail

ME_URI = "/people/@me"
MINIBLOG_URI = "/people/@me/miniblog"
MAIL_INBOX = "/doumail/inbox"
MAIL_OUTBOX = "/doumail/outbox"

class DoubanRobot(object):
    user = None
    def __init__(self, key=None, secret=None, api_key=None, api_secret=None):
        if api_key and api_secret:
            self.client = DoubanOAuth(api_key, api_secret)
        else:
            self.client = DoubanOAuth()
        if key and secret:
            self.client.login(key, secret)
    
    def get(self, url, param=None):
        return self.client.request('GET', url, param=param)

    def put(self, url, body=None):
        return self.client.request('PUT', url, body and body.encode('utf-8'))

    def post(self, url, body=None):
        return self.client.request('POST', url, body and body.encode('utf-8'))
        
    def get_mail_content(self, mail_id):
        """ get single mail's content """
        mail_id = mail_id.replace("http://api.douban.com/doumail/", "")
        jsondata = self.get("/doumail/" + mail_id, param={"keep-unread":"true", "alt":"json"}).read()
        data = json.loads(jsondata)
        return data["content"]["$t"]
        
    def get_mails(self, recv=True, start=1, cnt=50, uid=None, name=None):
        """ fetch mails"""
        url = MAIL_INBOX
        if not recv:
            url = MAIL_OUTBOX

#        try:
        jsondata = self.get(url, param={"max-results":str(cnt), "start-index": str(start), "alt":"json"}).read()
        data = json.loads(jsondata)
   #     except:
#            return []

        mail_list = []
        entries = data["entry"]
        for entry in entries:
            mid = entry["id"]["$t"].replace("http://api.douban.com/doumail/", "")
            mail = Mail.get_or_insert(key_name=mid)
            mail.id = mid
            mail.content = self.get_mail_content(mail.id)
            mail.title = entry["title"]["$t"]
            author = entry["author"]
            mail.author_name = author["name"]["$t"]
            mail.author_id = author["uri"]["$t"]
            mail.time = entry["published"]["$t"]
            mail.uid = uid
            mail.name = name
            mail.recv=recv
            mail.put()
            
            mail_list.append(mail)            
        return mail_list
    
    def get_auth_url(self):
        return self.client.auth_url()
    
    def get_access_token(self, token_key, token_secret):
        self.client.get_access_token(token_key, token_secret)
        
    def get_current_user(self):
        data = self.get(ME_URI, param={"alt":"json"}).read()
        account = Account()
        account.from_json(data)
        self.user = { "name":account.title, "uid":account.uid }
        return self.user
        
    @property
    def token_key(self):
        return self.client.token_key
    
    @property
    def token_secret(self):
        return self.client.token_secret


def escape(s):
    return urllib.quote(s, safe='~')
        

def test():
    from config import DB_API_KEY, DB_API_SECRET
    robot = DoubanRobot(api_key=DB_API_KEY, api_secret=DB_API_SECRET)
    raw_input(robot.get_auth_url())
    
    robot.get_current_user()
        
    
if __name__ == '__main__':
    test()