import hashlib
import re

import request
from nation import Nation


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
        # Perform action.
        if self.request.get('action'):
            action = self.request.get('action')
            # Login.
            if action == 'login':
                self.login(self.request.get('nation'), self.request.get('pwd'))
            # Logout.
            elif action == 'logout':
                self.logout()
                self.redirectToLogin()
            # Create.
            elif action == 'create':
                self.create(self.request.get('nation'), self.request.get('pwd'),
                            self.request.get('confirm'),
                            self.request.get('email'),
                            self.request.get('color1'),
                            self.request.get('color2'))
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
        self.deleteCookie('capitol')
        self.deleteCookie('pwd')

    def create(self, nation, password, confirm, email, color1, color2):
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
        elif not re.match(".+@.+\..{2,32}", email):
            error = 'Bad email address.'
        elif not re.match("[\da-fA-F]{6}", color1) or\
             not re.match("[\da-fA-F]{6}", color2):
            error = 'Bad color format (should be 6 digit hex).'
        elif color1 == color2:
            error = 'Colors cannot be the same.'
        else:
            n = Nation(nation, self.hashStr(password), email=email,
                       color1=int(color1, 16), color2=int(color2, 16),
                       create=True)
            if not n.exists():
                error = 'Nation already exists.'
        # Login.
        if error:
            self.errorPage(error)
        else:
            self.login(nation, password, verify=False)

    def errorPage(self, error):
        """Show a custom error page."""
        self.response.headers['Content-Type'] = 'text/plain'
        self.response.out.write('Error: ' + error)
