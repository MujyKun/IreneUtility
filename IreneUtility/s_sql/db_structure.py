from . import self
import aiofiles

"""
File meant for creating the DB Structure

There is a way to manually create the db structure from a file and also directly from code.
"""


async def create_db_structure_from_file(verbose=True):
    """
    Creates the db structure based on the existing version sql file.

    This prevents having the manually update the db structure across development bots.
    Before this method is used, there must be a SQL connection whether it is connected to another DB, or creating
    an empty DB with no schemas just to create the python connection.

    SQL File must be in the main directory of the Bot Client.

    Includes a blocking File IO Task, but since this is executed on start/run, it really does not matter.
    """
    try:
        async with aiofiles.open("./db_structure.sql", "r") as sql_file:
            db_structure = await sql_file.read()
    except FileNotFoundError:
        print("There was no DB Structure file named db_structure.sql in the main client directory found "
              "to update the DB.")
        return

    queries = db_structure.split(';')

    # we do not want to run the entire structure at once
    # separating it into queries will allow us to handle errors.
    for query in queries:
        try:
            query = query.replace("\n", "")
            if query.startswith("--"):
                continue
            await self.conn.execute(query)
        except Exception as e:
            if verbose:
                print(f"{e} -> Failed to execute query: {query} -> create_db_structure")
