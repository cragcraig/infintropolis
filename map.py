import random

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

from mapblock import MapBlock

class GetBlock(webapp.RequestHandler):
  """Retrive a Map Block."""

  def get(self):
    self.response.headers['Content-Type'] = 'text/plain'
    for i in range(50*50):
      v = random.randint(1,9)
      r = random.choice([2, 3, 3, 4, 4, 5, 5, 6, 6,
                         8, 8, 9, 9, 10, 10, 11, 11, 12])
      if v is 1:
        r = 0
      self.response.out.write('%s:%s,' % (str(v), str(r)))


application = webapp.WSGIApplication(
                                     [('/map/get.*', GetBlock)],
                                     debug=True)

def main():
  run_wsgi_app(application)

if __name__ == "__main__":
  main()
