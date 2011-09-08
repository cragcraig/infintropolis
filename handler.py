import random
import hashlib
import cgi

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

import request
from infbase import Vect
from mapblock import MapBlock

class GetBlock(request.Handler):
    """Handle MapBlock requests."""

    def get(self):
        """Return requested data."""
        self.response.headers['Content-Type'] = 'text/plain'

        # Check user.
        if not self.validateUser():
            return

        # Check coordinates.
        form = cgi.FieldStorage()
        if 'x' not in form or 'y' not in form:
            return

        # Retrieve MapBlock.
        block = MapBlock(Vect(form.getfirst('x'), form.getfirst('y')))
        self.response.out.write(block.getString())


class Session(request.Handler):
    """Handle session requests."""

    def get(self):
        form = cgi.FieldStorage()
        if 'action' in form:
            action = form.getfirst('action')
            # Login.
            if action == 'login' and 'nation' in form and 'pwd' in form:
                self.login(form.getfirst('nation'), form.getfirst('pwd'))
                return
            # Logout.
            elif action == 'logout':
                self.logout()
        # Display login page.
        self.redirectToLogin()

    def login(self, nation, password):
        hasher = hashlib.md5()
        hasher.update(password)
        hashedPwd = hasher.hexdigest()
        self.setCookie('nation', nation)
        self.setCookie('pwd', hashedPwd)
        self.redirect('/map')

    def logout(self):
        self.deleteCookie('nation')
        self.deleteCookie('pwd')


application = webapp.WSGIApplication(
                                     [('/', Session),
                                      ('/get/map.*', GetBlock),
                                      ('/session.*', Session)],
                                     debug=True)

def main():
  run_wsgi_app(application)

if __name__ == "__main__":
  main()
