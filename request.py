import cgi
import string

from google.appengine.ext import webapp

from nation import Nation


class Handler(webapp.RequestHandler):
    """Abstract request details.
    
    Provides methods covering cookies and browser redirects.
    """
    _nation = None
    _encodeMap = string.maketrans(' \'', '+*')
    _decodeMap = string.maketrans('+*', ' \'')

    def setCookie(self, key, value, timeout=99999):
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

    def redirect(self, url):
        """Redirect client browser."""
        self.response.set_status(303)
        self.response.headers['Location'] = url
        self.response.out.write('Redirecting to <a href="%s">%s</a>' %
                                (url, url))

    def redirectToLogin(self):
        self.redirect('/static/login.htm')

    def redirectToMap(self):
        self.redirect('/map')

    def loadNation(self):
        n = Nation(self.getCookie('nation'), self.getCookie('pwd'))
        if n.exists():
            self._nation = n
            return True
        else:
            return False

    def getNation(self):
        return self._nation
