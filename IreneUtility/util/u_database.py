from ..Base import Base
from . import u_logger as log
from discord.ext import tasks
from concurrent.futures import ThreadPoolExecutor
import asyncio


class DataBase(Base):
    def __init__(self, *args):
        super().__init__(*args)

    @tasks.loop(seconds=0, minutes=0, hours=0, reconnect=True)
    async def set_start_up_connection(self):
        """Looping Until A Stable Connection to DB is formed. This is to confirm Irene starts before the DB connects.
        Also creates thread pool and increases recursion limit.
        """
        if not self.ex:
            return

        if not self.ex.client.loop.is_running():
            return

        try:
            self.ex.conn = await self.get_db_connection()  # set the db connection
            self.ex.sql.self.conn = self.ex.conn
            self.ex.running_loop = asyncio.get_running_loop()  # set running asyncio loop
            await self.create_thread_pool()  # set new thread pool

            if self.ex.create_db_structure:
                await self.ex.sql.db_structure.create_db_structure()  # has blocking file io
        except Exception as e:
            log.console(f"{e} (Exception)", method=self.set_start_up_connection)
        self.set_start_up_connection.stop()  # stop this method from loop.

    async def create_thread_pool(self):
        self.ex.thread_pool = ThreadPoolExecutor()

    @tasks.loop(seconds=0, minutes=1, reconnect=True)
    async def show_irene_alive(self):
        """Looped every minute to send a connection to localhost:5123 to show bot is working well."""
        source_link = "http://127.0.0.1:5123/restartBot"
        async with self.ex.session.get(source_link):
            pass

    async def get_db_connection(self):
        """Retrieve Database Connection"""
        return await self.ex.keys.connect_to_db()
