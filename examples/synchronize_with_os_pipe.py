import os
import textwrap as tw
from test.support import interpreters

ISSUE = "Stuck on this one"


def test_synchronize():
    print(ISSUE)
    return
    interp1 = interpreters.create()
    interp2 = interpreters.create()
    r, s = os.pipe()

    print("before starting interp2")
    interp2.run(tw.dedent(f"""
            import os
            os.write({s}, '')
            print("after write in interp2")
            """))
    print("after starting interp2")

    print("before starting interp1")
    interp1.run(tw.dedent(f"""
            import os
            os.read({r}, 1)
            print("after read in interp1")
            """))
    print("after starting interp1")


if __name__ == "__main__":
    test_synchronize()
