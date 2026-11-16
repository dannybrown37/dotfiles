tag: browser
and tag: user.rango_disabled
-
# One-letter hints already work: community presses the letter.
<user.letter> <user.letter>: insert(letter_1 + letter_2)

# Tab markers ("N | title") go through the clipboard too, so cycle tabs until
# the window title starts with the marker.
(go tab | slot) <user.letter>: user.chrome_go_tab_marker(letter)
(go tab | slot) <user.letter> <user.letter>:
    user.chrome_go_tab_marker(letter_1 + letter_2)
