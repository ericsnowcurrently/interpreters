import textwrap as tw
from test.support import interpreters

def test_exception_handling():
    interp = interpreters.create()
    try:
        interp.run(tw.dedent("""
            raise KeyError
            """))
    except interpreters.RunFailedError as exc:
        print(f"Expecting KeyError from the subinterpreter, got: {exc}")


if __name__ == "__main__":
    test_exception_handling()
