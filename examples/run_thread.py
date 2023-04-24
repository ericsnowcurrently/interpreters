import threading
from test.support import interpreters


def test_run_thread():
    interp = interpreters.create()
    def run():
        interp.run('print("during")')
    t = threading.Thread(target=run)
    print("before")
    t.start()
    t.join()
    print("after")


if __name__ == "__main__":
    test_run_thread()
