# Exercises all module functions, and shows that
# the main Interpreter(id=0, ...) was already there
from pprint import pformat
from test.support import interpreters


def test_module_functions():
    interps = [interpreters.create() for _ in range(4)]
    print(f"interps = {pformat(interps)}")
    all = interpreters.list_all()
    print(f"all = {pformat(all)}")
    print(f"{interpreters.get_current() = }")
    print(f"{interpreters.get_main() = }")


if __name__ == "__main__":
    test_module_functions()
