from test.support import interpreters
from threading import Thread

interp = interpreters.create()

def t():
    interp.run("while True: pass")

thread = Thread(target = t)
thread.start()
# Should see this but it never gets there:
print(f"{interp.is_running() = }")
