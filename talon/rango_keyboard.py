import os

from talon import Context

# Purview DLP on the work PC likely blocks Rango's clipboard requests
# ("Clipboard is empty"), so there Rango's voice commands are off. Hints are
# clicked by typing their letters (Rango keyboard clicking +
# rango_keyboard.talon).
ctx = Context()
ctx.matches = 'tag: browser'
if os.environ.get('USERDOMAIN', '').upper() == 'WHELEN':
    ctx.tags = ['user.rango_disabled']
