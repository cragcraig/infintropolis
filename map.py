import random
import cgi

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

from infbase import Vect
from mapblock import MapBlock

class GetBlock(webapp.RequestHandler):
  """Retrive a Map Block."""

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


application = webapp.WSGIApplication(
                                     [('/map/get.*', GetBlock)],
                                     debug=True)

def main():
  run_wsgi_app(application)

if __name__ == "__main__":
  main()
