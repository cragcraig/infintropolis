import random
import cgi

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

from infbase import Vect
from mapblock import MapBlock

class Getter(webapp.RequestHandler):
  """Handle data requests."""

  def get(self):
    """Returns a requested MapBlock."""
    self.response.headers['Content-Type'] = 'text/plain'

    # check coordinates
    form = cgi.FieldStorage()
    if 'x' not in form or 'y' not in form:
        return

    # retrieve MapBlock
    block = MapBlock(Vect(form.getfirst('x'), form.getfirst('y')))
    self.response.out.write(block.getString())


class Session(webapp.RequestHandler):
    """Handle session requests."""

    def get(self):
        form = cgi.FieldStorage()
        if 'action' not in form:
            self.redirect('/login.htm')

    def setCookie(self, key, value, timeout=99999):
        """Add a cookie to the header."""
        self.response.headers.add_header('Set-Cookie',
                                         key + '=' + value + '; '
                                         'max-age=' + repr(int(timeout)) + '; '
                                         'path=/;')

    def getCookie(self, key):
        """Read the contents of a cookie."""
        return self.request.cookies.get(key)

    def deleteCookie(self, key):
        """Delete a cookie from the client browser."""
        self.setCookie(key, '', timeout=-1)

    def redirect(self, url):
        self.response.headers['Location'] = url
        

application = webapp.WSGIApplication(
                                     [('/map/get.*', Getter),
                                      ('/session.*', Session)],
                                     debug=True)

def main():
  run_wsgi_app(application)

if __name__ == "__main__":
  main()
