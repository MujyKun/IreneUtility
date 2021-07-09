class Command:
    def __init__(self, cog_name, command_name, description, example_image_url, syntax, example_syntax,
                 permissions_needed, aliases, notes):
        """
        Bot Command meant for a more detailed help command if command details were written outside of the Bot.

        This should not be confused with a discord.py Command object.

        :param cog_name: (str) The cog name that the command belongs to.
        :param command_name: (str) The command's name.
        :param description: (str) Description of the command.
        :param example_image_url: (str) Image URL of the command being used.
        :param syntax: (str) Syntax format.
        :param example_syntax: (str) Example of the syntax.
        :param permissions_needed: (list) Customized Permissions
        :param aliases: (list) Aliases of the command
        :param notes: (str) Extra notes related to the command.
        """
        self.cog_name: str = cog_name
        self.command_name: str = command_name
        self.description: str = description
        self.example_image_url: str = example_image_url
        self.syntax: str = syntax
        self.example_syntax: str = example_syntax
        self.permissions_needed: list = permissions_needed
        self.aliases: list = aliases
        self.notes: str = notes
