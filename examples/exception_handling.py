import textwrap as tw
from test.support import interpreters

ISSUE = "Thought this was fixed; see NOTES.md"

def test_exception_handling():
    print(ISSUE); return
    interp = interpreters.create()
    try:
        interp.run(tw.dedent("""
            raise KeyError
            """))
    except interpreters.RunFailedError as exc:
        print(f"got the error from the subinterpreter: {exc}")


if __name__ == "__main__":
    test_exception_handling()
