import cgi
import string
#import json
import simplejson as json

#import webapp2
from google.appengine.ext import webapp

from nation import Nation


#class Handler(webapp2.RequestHandler):
class Handler(webapp.RequestHandler):
    """Abstract request details.
    
    Provides methods covering cookies and browser redirects.
    """
    _nation = None
    _encodeMap = string.maketrans(' \'', '+*')
    _decodeMap = string.maketrans('+*', ' \'')

    def setCookie(self, key, value, timeout=999999):
        """Add a cookie to the header."""
        value = value.encode('ascii').translate(self._encodeMap)
        self.response.headers.add_header('Set-Cookie',
                                         key + '=' + value + '; '
                                         'max-age=' + str(timeout) + '; '
                                         'path=/;')

    def getCookie(self, key):
        """Read the contents of a cookie."""
        value = self.request.cookies.get(key)
        if value:
            return value.encode('ascii').translate(self._decodeMap)
        else:
            return value

    def deleteCookie(self, key):
        """Delete a cookie from the client browser."""
        self.setCookie(key, '', timeout=-1)

    def inDict(self, dictionary, *args):
        """Returns True if all strings passed exist in dictionary."""
        for i in args:
            if i not in dictionary:
                return False
        return True

    def redirect(self, url):
        """Redirect client browser."""
        self.response.set_status(303)
        self.response.headers['Location'] = url
        self.response.out.write('Redirecting to <a href="%s">%s</a>' %
                                (url, url))

    def redirectToLogin(self):
        """Redirect the client browser to the login page."""
        self.redirect('/static/login.htm')

    def redirectToMap(self):
        """Redirect the client browser to the main game page."""
        self.redirect('/map')

    def loadNation(self):
        """Load the nation the client is logged in as."""
        nation = self.getCookie('nation')
        pwd = self.getCookie('pwd')
        if not nation or not pwd:
            return False
        n = Nation(nation, pwd)
        if n.exists():
            self._nation = n
            return True
        else:
            return False

    def writeLogoutJSON(self):
        self.writeJSON({'logout': True})

    def writeJSON(self, obj):
        """Write a Python object out as a JSON string."""
        self.response.headers['Content-Type'] = 'text/plain'
        j = json.JSONEncoder().encode(obj)
        self.response.out.write(j)

    def getJSONRequest(self):
        return json.loads(self.request.get('request'))

    def getNation(self):
        return self._nation
