# Running an interpreter in a Thread
# Shows different run states of the interpreter
import textwrap as tw
from test.support import interpreters
from threading import Thread


def test_threading_interpreter():
    interp = interpreters.create()

    def t():
        interp.run(tw.dedent("""
            import time
            for _ in range(50):
                print(end='.', flush=True)
                time.sleep(0.05)
            print("End of interp job")
        """))

    thread = Thread(target = t)
    print(f"Before thread.start(), {interp.is_running() = }")
    thread.start()
    print(f"After thread.start(), {interp.is_running() = }")
    thread.join()
    print(f"After thread.join(), {interp.is_running() = }")


if __name__ == "__main__":
    test_threading_interpreter()
