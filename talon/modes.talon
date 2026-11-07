mode: command
mode: dictation
-
# (…)+ still matches when a missed first try gets repeated before the pause.
# Trailing words skip the pause: "start typing hello" types hello,
# "stop typing pane left" runs pane left.
^(start typing)+ [<user.text>]$: user.start_typing(text or "")
^(stop typing)+ [<user.text>]$: user.stop_typing(text or "")
