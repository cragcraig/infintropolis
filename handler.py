import random
import hashlib
import cgi
import re

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

import request
from inf import Vect
from mapblock import MapBlock
from nation import Nation

class GetBlock(request.Handler):
    """Handle MapBlock requests."""

    def get(self):
        """Return requested data."""
        self.response.headers['Content-Type'] = 'text/plain'

        # Check user.
        if not self.loadNation():
            self.response.out.write("'" + self.getCookie('nation') + "'")
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
        """Handle all GET session logic."""
        self.logic()

    def post(self):
        """Handle all POST session logic."""
        self.logic()

    def logic(self):
        """Handle all session logic."""
        form = cgi.FieldStorage()
        # Perform action.
        if 'action' in form:
            action = form.getfirst('action')
            # Login.
            if action == 'login':
                self.login(form.getfirst('nation'), form.getfirst('pwd'))
            # Logout.
            elif action == 'logout':
                self.logout()
                self.redirectToLogin()
            # Create.
            elif action == 'create':
                self.create(form.getfirst('nation'), form.getfirst('pwd'),
                            form.getfirst('confirm'), form.getfirst('email'))
            else:
                self.redirectToLogin()
        # Already logged in, go to map.
        elif self.getCookie('nation') and self.getCookie('pwd'):
            self.redirectToMap()
        # No action, show login page.
        else:
            self.redirectToLogin()

    def hashStr(self, string):
        """Create a hash of string using the MD5 algorithm."""
        hasher = hashlib.md5()
        hasher.update(string)
        return hasher.hexdigest()

    def login(self, nation, password, verify=True):
        """Establish a session."""
        hashedPwd = self.hashStr(password)
        if not verify or Nation(nation, hashedPwd).exists():
            self.setCookie('nation', nation)
            self.setCookie('pwd', hashedPwd)
            self.redirectToMap()
        else:
            self.redirectToLogin()

    def logout(self):
        """End a session."""
        self.deleteCookie('nation')
        self.deleteCookie('pwd')

    def create(self, nation, password, confirm, email):
        """Create a new nation."""
        error = None
        # Check fields.
        if not nation or not password or not confirm or not email:
            error = 'Missing field.'
        elif (not re.match("[\w\d -]{3,32}$", nation) or
              re.search("--", nation) or nation != nation.strip()):
            error = 'Bad nation name.'
        elif len(password) < 6 or len(password) > 16:
            error = 'Bad password length.'
        elif password != confirm:
            error = 'Passwords do not match.'
        elif not re.match("\w+@\w+\.\w{2,32}", email):
            error = 'Bad email address'
        else:
            n = Nation(nation, self.hashStr(password), email=email, create=True)
            if not n.exists():
                error = 'Nation already exists.'
        # Login.
        if error:
            self.errorPage(error)
        else:
            self.login(nation, password, verify=False)

    def errorPage(self, error):
        """Show a session error page."""
        self.response.headers['Content-Type'] = 'text/plain'
        self.response.out.write('Error: ' + error)


application = webapp.WSGIApplication(
                                     [('/', Session),
                                      ('/get/map.*', GetBlock),
                                      ('/session.*', Session)],
                                     debug=True)

def main():
  run_wsgi_app(application)

if __name__ == "__main__":
  main()
