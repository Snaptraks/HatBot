from datetime import datetime, timedelta


class UserProfile:
    def __init__(self, member):
        self.member_id = member.id
        self.tokens = []
        # message cooldown that won't count towards exp
        self.cooldown = timedelta(minutes=5)
        # message expiration time; after that time exp expires and is removed
        self.expiration = timedelta(weeks=1)
        # last token, or last message. by default set it as minimum value
        self._last_token = datetime.min

    @property
    def exp(self):
        """Returns the exp of the user."""
        self._check_exp()
        return len(self.tokens)

    def give_exp(self, message):
        """Saves the token, if it has been longer than the cooldown."""
        token = message.created_at
        if (datetime.utcnow() - self._last_token) > self.cooldown:
            self.tokens.append(token)
        self._check_exp()

    def _check_exp(self):
        """Remove expired tokens, if needed."""
        self.tokens = [t for t in self.tokens
                       if (datetime.utcnow() - t) < self.expiration]
        try:
            self._last_token = max(self.tokens)
        except ValueError as e:
            # empty sequence in max(), set as minimum value
            self._last_token = datetime.min

    def __repr__(self):
        return f'<{self.__class__.__name__} id={self.member_id} exp={self.exp}>'
