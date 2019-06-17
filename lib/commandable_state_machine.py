from typing import Callable, Dict, Tuple

from lib.vsm import VSM


class CommandNotFoundException(Exception):
    pass


class CommandableStateMachine(VSM):
    def __init__(self):
        super().__init__()

        self._commands: Dict[str, Tuple[str, Callable]] = {}

    def _register_command(self, key: str, description: str, action: Callable):
        self._commands[key] = (description, action)

    def _show_help(self, help_text: str):
        if help_text:
            print(help_text)

        for key, content in self._get_all_commands().items():
            help_text, _ = content

            if not help_text:
                continue

            print("{}: {}".format(key.upper(), help_text))

    def _ask_for_cmd(self):
        # Ask the user for input. Technically, they could've entered a command
        # at any time. The actual `input`-call which captures this input is in
        # `_start_kbd_capture()`.
        print("Enter a command and press return: ", end="", flush=True)

    def _get_all_commands(self):
        all_commands = self._commands
        if isinstance(self.current_state, CommandableStateMachine):
            for key, command in self.current_state._get_all_commands().items():
                all_commands[key] = command
        return all_commands

    def _get_command(self, command: str) -> Tuple[str, Callable]:
        if command not in self._commands:
            raise CommandNotFoundException("The command {} is not vaild."
                                           .format(command))

        return self._commands[command]

    def _execute_command(self, input_: str):
        """Checks if the input corresponds to a command and executes it."""

        try:
            _, action = self._get_command(input_)

            new_state = action()

            if new_state and isinstance(new_state, type(VSM)):
                return new_state
        except CommandNotFoundException:
            # TODO Let the user know, that the input was not a valid command?
            pass

        if isinstance(self.current_state, CommandableStateMachine):
            return self.current_state._execute_command(input_)
