from test.support import interpreters


def test_run_isolated():
    interp = interpreters.create()
    print("before")
    interp.run('print("during")')
    print("after")

if __name__ == "__main__":
    test_run_isolated()
