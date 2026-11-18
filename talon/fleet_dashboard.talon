app: windows_terminal
# .tmux.conf titles windows "tmux <session>:<window>"; the dashboard is fleet:dash
title: /^tmux fleet:dash/
mode: command
-
agent next: key(j)
agent last: key(k)
agent top: key(g)
agent jump: key(enter)
agent go: user.fleet_send("go")
agent send <user.text>: user.fleet_send(text)
agent diff: key(d)
agent draft: key(p)
agent browser: key(o)
agent new: key(n)
agent stop: key(X)
agent lazy git: key(L)
show agents: key(1)
show reviews: key(2)
show mine: key(3)
review this: key(r)
review deep: key(a)
fleet palette: key(ctrl-p)
