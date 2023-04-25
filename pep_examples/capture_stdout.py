import contextlib
import io
import textwrap as tw
from test.support import interpreters

ISSUE = "stdout not getting captured"

def test_capture_stdout():
    print(ISSUE)
    interp = interpreters.create()
    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        interp.run(tw.dedent("""
                print('spam!')
                """))
    result = stdout.getvalue()
    print(f"{result = }, should be 'spam!'")
    # assert(stdout.getvalue() == 'spam!')


if __name__ == "__main__":
    test_capture_stdout()
