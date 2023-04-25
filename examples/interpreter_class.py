# Uses 'Interpreter' methods
from test.support import interpreters
from threading import Thread


def test_interpreter_class():
    interp = interpreters.create()

    def show(msg):
        print(msg)
        print(f"{interp = }")
        print(f"{interp.id = }")
        print(f"{interp.is_running() = }")
        print("-" * 20)

    def t():
        show("In t(), before sleep(3)")
        interp.run("import time; time.sleep(3)")
        show("In t(), after sleep(3)")

    thread = Thread(target = t)
    show("Before thread.start()")
    thread.start()
    show("After thread.start()")
    # interp.close()  # Produces RuntimeError
    thread.join()
    show("After thread.join()")
    interp.close(); # OK because the interpreter is no longer running
    # show("After interp.close()") # interp.is_running() fails


if __name__ == "__main__":
    test_interpreter_class()
