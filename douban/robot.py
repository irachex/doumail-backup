#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import logging
import codecs
import urllib
try:
    import simplejson as json
except:
    import json

from client import OAuthClient
from model import Account, Mail

API_SERVER = 'http://api.douban.com'
ME_URI = API_SERVER + "/people/%40me"
MINIBLOG_URI = API_SERVER + "/people/%40me/miniblog"
MAIL_INBOX = API_SERVER + "/doumail/inbox"
MAIL_OUTBOX = API_SERVER + "/doumail/outbox"

class DoubanRobot(OAuthClient):
    user = None
    
    def get(self, url, body=None, params=None):
        return self.access_resource('GET', url, body=body, params=params)

    def put(self, url, body=None, params=None):
        return self.access_resource('PUT', url, body and body.encode('utf-8'), params=None)

    def post(self, url, body=None, params=None):
        return self.access_resource('POST', url, body and body.encode('utf-8'), params=None)
        
    def get_mail_content(self, mail_id):
        """ get single mail's content """
        mail_id = mail_id.replace("http://api.douban.com/doumail/", "")
        jsondata = self.get(API_SERVER + "/doumail/" + mail_id, params={"keep-unread":"true", "alt":"json"}).read()
        data = json.loads(jsondata)
        return data["content"]["$t"]
        
    def get_mails(self, recv=True, start=1, cnt=50, uid=None, name=None):
        """ fetch mails"""
        url = MAIL_INBOX
        if not recv:
            url = MAIL_OUTBOX

#        try:
        jsondata = self.get(url, params={"max-results":str(cnt), "start-index": str(start), "alt":"json"}).read()
        data = json.loads(jsondata)
   #     except:
#            return []

        mail_list = []
        entries = data["entry"]
        for entry in entries:
            try:
                mid = entry["id"]["$t"].replace("http://api.douban.com/doumail/", "")
                mail = Mail.get_or_insert(key_name=mid)
                mail.id = mid
                mail.content = self.get_mail_content(mail.id)
                mail.title = entry["title"]["$t"].replace("\n", "");
                author = entry["author"]
                mail.author_name = author["name"]["$t"]
                mail.author_id = author["uri"]["$t"]
                mail.time = entry["published"]["$t"]
                mail.uid = uid
                mail.name = name
                mail.recv=recv
                mail.put()
            except:
                logging.info(entry)
            mail_list.append(mail)            
        return mail_list
        
    def get_current_user(self):
        data = self.get(ME_URI, params={"alt":"json"}).read()
        logging.info( data)
        account = Account()
        account.from_json(data)
        self.user = { "name":account.title, "uid":account.uid }
        return self.user


def escape(s):
    return urllib.quote(s, safe='~')
        

def test():
    from config import DB_API_KEY, DB_API_SECRET
    robot = DoubanRobot(key=DB_API_KEY, secret=DB_API_SECRET)
    key, secret = robot.get_request_token()
    raw_input(robot.get_authorization_url(key, secret))
    
    robot.get_current_user()
        
    
if __name__ == '__main__':
    test()