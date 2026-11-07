mode: command
-
^chief waiting$: user.chief_send("Is anything waiting on me?")
^chief status$: user.chief_send("Give me a one-line status of every agent.")
^chief say <user.text>$: user.chief_send(text)
^chief sleep$: speech.disable()
