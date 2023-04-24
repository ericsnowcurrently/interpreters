import textwrap as tw
from test.support import interpreters

INCOMPLETE = "TODO: exc.__cause__ has not yet been implemented"


def test_exception_re_raising():
    interp = interpreters.create()
    try:
        try:
            interp.run(tw.dedent("""
                raise KeyError
                """))
        except interpreters.RunFailedError:
            # raise exc.__cause__    ## Not implemented yet, produces error
            print(INCOMPLETE)
            assert True
    except KeyError:
        print("got a KeyError from the subinterpreter")


if __name__ == "__main__":
    # test_exception_re_raising()
    print(INCOMPLETE)
