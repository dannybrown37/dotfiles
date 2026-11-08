app: windows_terminal
mode: command
mode: dictation
-
# No trailing space, so the CLI's menu stays open: "enter" runs the top
# match, "space" starts the arguments.
slash <user.slash_command>: insert("/{slash_command}")
