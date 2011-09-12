import cgi

from google.appengine.ext import webapp


class Handler(webapp.RequestHandler):
    """Abstract request details.
    
    Provides methods covering cookies and browser redirects."""

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
        """Redirect client browser."""
        self.response.set_status(303)
        self.response.headers['Location'] = url
        self.response.out.write('Redirecting to <a href="%s">%s</a>' %
                                (url, url))

    def redirectToLogin(self):
        self.redirect('/static/login.htm')

    def validateNation(self):
        return self.getCookie('nation') and self.getCookie('pwd')
