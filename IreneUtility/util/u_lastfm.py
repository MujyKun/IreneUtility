from ..Base import Base
from . import u_logger as log


# noinspection PyPep8
class LastFM(Base):
    def __init__(self, *args):
        super().__init__(*args)

    def create_fm_payload(self, method, user=None, limit=None, time_period=None):
        """Creates the payload to be sent to Last FM"""
        payload = {
            'api_key': self.ex.keys.last_fm_api_key,
            'method': method,
            'format': 'json'
        }
        if user:
            payload['user'] = user
        if limit:
            payload['limit'] = limit
        if time_period:
            payload['period'] = time_period
        return payload

    async def get_fm_response(self, method, user=None, limit=None, time_period=None):
        """Receives the response from Last FM"""
        async with self.ex.session.get(self.ex.keys.last_fm_root_url, headers=self.ex.keys.last_fm_headers,
                                       params=self.create_fm_payload(method, user, limit, time_period)) as response:
            return await response.json()

    async def get_fm_username(self, user_id):
        """Gets Last FM username from the DB."""
        return self.ex.first_result(await self.ex.conn.fetchrow("SELECT username FROM lastfm.users WHERE userid = $1", user_id))

    async def set_fm_username(self, user_id, username):
        """Sets Last FM username to the DB."""
        try:
            if not await self.get_fm_username(user_id):
                await self.ex.conn.execute("INSERT INTO lastfm.users(userid, username) VALUES ($1, $2)", user_id, username)
            else:
                await self.ex.conn.execute("UPDATE lastfm.users SET username = $1 WHERE userid = $2", username, user_id)
            return True
        except Exception as e:
            log.console(e)
            return e


# self.ex.u_last_fm = LastFM()
