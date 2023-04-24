import textwrap as tw
from test.support import interpreters

ISSUE = "TODO: exc.__cause__ has not yet been implemented"


def test_exception_re_raising():
    print(ISSUE); return
    interp = interpreters.create()
    try:
        try:
            interp.run(tw.dedent("""
                raise KeyError
                """))
        except interpreters.RunFailedError:
            raise exc.__cause__    ## Not implemented yet, produces error
    except KeyError:
        print("got a KeyError from the subinterpreter")


if __name__ == "__main__":
    test_exception_re_raising()

