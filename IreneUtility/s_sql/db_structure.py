from IreneUtility.s_sql import self


async def create_db_structure():
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
