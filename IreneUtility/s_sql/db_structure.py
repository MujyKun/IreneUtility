from . import self

"""
File meant for creating the DB Structure

There is a way to manually create the db structure from a file and also directly from code.
"""


async def create_db_structure_from_file():
    """
    Creates the db structure based on the existing version sql file.

    This prevents having the manually update the db structure across development bots.
    Before this method is used, there must be a SQL connection whether it is connected to another DB, or creating
    an empty DB with no schemas just to create the python connection.

    SQL File must be in the main directory of the Bot Client.

    Includes a blocking File IO Task, but since this is executed on start/run, it really does not matter.
    """
    sql_file = open("./db_structure.sql", "r")
    db_structure = sql_file.read()
    sql_file.close()

    queries = db_structure.split(';')

    for query in queries:
        try:
            query = query.replace("\n", "")
            if query.startswith("--"):
                continue
            await self.conn.execute(query)
        except Exception as e:
            print(f"{e} -> Failed to execute query: {query} -> create_db_structure")


async def get_db_info():
    """Gets current connection information.

    :returns: current username, database name, and the version info.
    """
    user_name, db_name, version = (await self.conn.fetch("SELECT current_user, current_database(), version()"))[0]
    return user_name, db_name, version


async def create_schemas():
    schema_list = ["archive", "biasgame", "blackjack", "currency", "dreamcatcher", "general", "gg", "groupmembers",
                   "kiyomi", "lastfm", "logging", "patreon", "reminders", "selfassignroles", "stats", "testdb",
                   "twitch", "twitter", "vlive", "weverse", "youtube"]
    user, db_name, version = await get_db_info()

    for schema in schema_list:
        schema_query = f"""CREATE SCHEMA IF NOT EXISTS {schema} AUTHORIZATION {user}"""
        await self.conn.execute(schema_query)


async def create_tables():
    pass
