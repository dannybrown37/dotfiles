mode: dictation
-
# modes.talon's ^ anchor misses "stop typing" said mid-sentence: the whole
# utterance got typed. Keep the words before it and run the words after.
<user.raw_prose> stop typing [<user.text>]$:
    user.dictation_insert(raw_prose)
    user.stop_typing(text or "")
