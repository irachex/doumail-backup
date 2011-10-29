#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import os
import logging
import random
import urllib
import datetime
import uuid

from google.appengine.api import memcache
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.api import taskqueue
from google.appengine.api import mail
from google.appengine.ext import db

from model import Account, Mail
from douban.robot import DoubanRobot
from config import DB_API_KEY, DB_API_SECRET


class BaseHandler(webapp.RequestHandler):
    def get_current_session(self):
        value = None
        if "sid" in self.request.cookies:
            value = self.request.cookies["sid"]
        if not value:
            value = str(uuid.uuid4())
            self.response.headers.add_header('Set-Cookie','%s=%s; expires=%s; path=/;' % ("sid", value, datetime.datetime.now() + datetime.timedelta(hours=1)))
        return value
    
    def set_session(self, key, value):
        sid = self.get_current_session()
        return memcache.set(key=(sid+key), value=value, time=3600)
        
    def get_session(self, key):
        sid = self.get_current_session()
        return memcache.get(sid+key)
    
    def clear_session(self):
        sid = self.get_current_session()
        if not sid:
            return
        memcache.delete(sid+"uid")
        memcache.delete(sid+"email")
        expires = datetime.datetime.now() - datetime.timedelta(weeks=2)
        self.response.headers.add_header("Set-Cookie", "sid=;expires=%s; path=/" % expires)
            
    def render(self, template_name, data=None):
        temp_path = os.path.join(os.path.dirname(__file__), 'template/%s' % (template_name,))
        self.response.out.write(template.render(temp_path, data))
    
    def render_string(self, template_name, data=None):
        temp_path = os.path.join(os.path.dirname(__file__), 'template/%s' % (template_name,))
        return template.render(temp_path, data)
        
    

class HomeHandler(BaseHandler):
    def get(self):
        uid = self.get_session("uid")
        email = self.get_session("email")
        if uid is None:
            self.redirect("/auth/")
        elif email is None:
            self.redirect("/option/")
        else:
            self.redirect("/done/")
        

class AuthHandler(BaseHandler):
    def get(self):
        uid = self.get_session("uid") 
        if uid is not None:
            self.redirect("/option/")
        
        doubanbot = DoubanRobot(api_key=DB_API_KEY, api_secret=DB_API_SECRET)

        callback = self.request.get("callback").strip()
        if callback == "true":
            token_key = self.request.get("oauth_token").strip()
            token_secret = self.request.get("oauth_secret").strip()
            doubanbot.get_access_token(token_key, token_secret)
            account = doubanbot.get_current_user()
            #self.render("msg.html", {"msg":"墙挡住了我和豆瓣,等会儿再试试吧", "url":"/"})
            #    return
            
            self.set_session("token_key", doubanbot.token_key)
            self.set_session("token_secret", doubanbot.token_secret)
            self.set_session("uid", account["uid"])
            self.set_session("name", account["name"])
            
            self.redirect("/")
        
        try:
            douban_url = doubanbot.get_auth_url()
        except Exception,e:
            logging.info(e)
            self.render("msg.html", {"msg":"墙挡住了我和豆瓣,等会儿再试试吧", "url":"/"})
            return
        temp_data = {"douban_url": douban_url + "&oauth_callback=" + escape(self.request.url+"?callback=true&oauth_secret=" + doubanbot.token_secret)}
        self.render("auth.html", temp_data)
    

class OptionHandler(BaseHandler):
    def get(self):
        uid = self.get_session("uid") 
        if uid is None:
            self.redirect("/auth/")
        email = self.get_session("email")
        if email is not None:
            self.redirect("/done/")
        self.render("option.html", { "uid" : self.get_session("uid"),
                                     "name" : self.get_session("name"),
                                   });
    
    def post(self):
        email = escape(self.request.get("email"))
        self.set_session("email", email)
        
        uid = self.get_session("uid")
        user = Account.get_or_insert(key_name=uid)
        user.uid = uid
        user.email = email
        user.title = self.get_session("name")
        user.token_key = self.get_session("token_key")
        user.token_secret = self.get_session("token_secret")
        user.put()
        
        fqueue = taskqueue.Queue(name='fetch')
        ftask = taskqueue.Task(url='/fetch/', 
                               params={
                                   "uid": user.uid, 
                                   "email": user.email, 
                                   "title":user.title, 
                                   "token_key":user.token_key, 
                                   "token_secret":user.token_secret , 
                                   "recv":True, 
                                   "start":1, 
                                   "count":35, 
                                   "total":0
                               }) 
        fqueue.add(ftask)
        
        self.redirect("/done/")


class DoneHandler(BaseHandler):
    def get(self):
        uid = self.get_session("uid") 
        if uid is None:
            self.redirect("/auth/")
        email = self.get_session("email")
        if email is None:
            self.redirect("/option/")
        
        self.render("done.html", { "uid" : self.get_session("uid"),
                                   "name" : self.get_session("name"),
                                 });


class AboutHandler(BaseHandler):
    def get(self):
        uid="iRachex"
        email = "irachex@gmail.com"
        mail_list = db.GqlQuery("SELECT * FROM Mail WHERE uid=:1", uid)
        recvmails = self.render_string("doumail.txt", {"mails":mail_list})
       
        mail_list = db.GqlQuery("SELECT * FROM Mail WHERE uid=:1", uid)
        sendmails = self.render_string("doumail.txt", {"mails":mail_list})
        
        mail.send_mail(sender="irachex@gmail.com",
                       to=email,#.replace("%40", "@"),
                       subject="豆邮备份",
                       body="""
                       你的豆邮备份
                       """,
                       attachments=[("收件箱.txt",recvmails),("发件箱.txt",sendmails)])
        
        self.render("about.html")

        
class LogoutHandler(BaseHandler):
    def get(self):
        self.clear_session()
        self.redirect("/")
    
    
class FetchHandler(BaseHandler):
    def post(self):
        uid = self.request.get("uid")
        email = self.request.get("email")
        title = self.request.get("title")
        token_key = self.request.get("token_key")
        token_secret = self.request.get("token_secret")
        recv = eval(self.request.get("recv"))
        start = self.request.get("start")
        count = self.request.get("count")
        total = self.request.get("total")
        
        doubanbot = DoubanRobot(token_key, token_secret, DB_API_KEY, DB_API_SECRET)
        try:
            mail_list = doubanbot.get_mails(recv=recv, start=start, cnt=count, uid=uid, name=title)
        except:
            logging.info("stop task %s %s %s %s" %(uid, recv, start, total))
            return
        #    self.render("msg.html", {"msg":"豆邮太多收不过来了，请稍后再试吧", "url":"/"})
        if not mail_list:
            if recv:
                recv = False
            else:
                mail_list = db.GqlQuery("SELECT * FROM Mail WHERE uid=:1 AND recv=:2", uid, True)
                recvmails = self.render_string("doumail.txt", {"mails":mail_list})

                mail_list = db.GqlQuery("SELECT * FROM Mail WHERE uid=:1 AND recv=:2", uid, False)
                sendmails = self.render_string("doumail.txt", {"mails":mail_list})
                
                mail.send_mail(sender="irachex@gmail.com",
                               to=email.replace("%40", "@"),
                               subject="豆邮备份",
                               body="""
                               你的豆邮备份
                               """,
                               attachments=[("收件箱.txt",recvmails),("发件箱.txt",sendmails)])
                return
        fqueue = taskqueue.Queue(name='fetch')
        ftask = taskqueue.Task(url='/fetch/', 
                               params={
                                   "uid": uid, 
                                   "email": email, 
                                   "title": title, 
                                   "token_key": token_key, 
                                   "token_secret": token_secret,
                                   "recv":recv, 
                                   "start":int(start)+int(count), 
                                   "count":count, 
                                   "total":int(total)+int(count)
                               })
        fqueue.add(ftask)
                

def escape(s):
    return urllib.quote(s, safe='~')
         
