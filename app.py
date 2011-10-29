#!/usr/bin/env python
# -*- coding: UTF-8 -*-
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

import handler
                    
                           
application = webapp.WSGIApplication([
                   (r'/', handler.HomeHandler),
                   (r'/auth/', handler.AuthHandler),
                   (r'/option/', handler.OptionHandler),
                   (r'/done/', handler.DoneHandler),
                   (r'/logout/', handler.LogoutHandler),
                   (r'/about/', handler.AboutHandler),
                   (r'/fetch/', handler.FetchHandler),
              ], debug=True)

def main():
    run_wsgi_app(application)


if __name__ == "__main__":
    main()