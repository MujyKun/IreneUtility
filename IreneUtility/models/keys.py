from IreneUtility.util import u_logger as log
import asyncpg


class Keys:
    def __init__(self, **kwargs):
        self.postgres_options = None
        self.db_conn = None
        pass

    async def connect_to_db(self):
        """Create a pool to the postgres database using asyncpg"""
        # pool is not being used as recommended, however, since we do not deal with millions of requests a second,
        # the current usage is fine. connections from the pool are also not released after completion and we let asyncpg
        # release the inactive connection once it recognizes it is inactive.
        # instead of acquiring a connection from the pool, we just let the pool select a connection for us and
        # execute directly that way. this limits the amount of methods we have access to,
        # but in the case those methods are needed, just acquire the connection and use that instead.
        self.db_conn = await asyncpg.create_pool(**self.postgres_options, command_timeout=60)
        return self.db_conn
