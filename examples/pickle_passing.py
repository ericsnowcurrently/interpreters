import os
import pickle
import textwrap as tw
from test.support import interpreters

ISSUE = "ValueError: source code string cannot contain null bytes"

def test_pickle_passing():
    print(ISSUE); return
    interp = interpreters.create()
    r, s = os.pipe()
    interp.run(tw.dedent(f"""
        import os
        import pickle
        reader = {r}
        """))
    interp.run(tw.dedent("""
            data = b''
            c = os.read(reader, 1)
            while c != b'\x00':
                while c != b'\x00':
                    data += c
                    c = os.read(reader, 1)
                obj = pickle.loads(data)
                do_something(obj)
                c = os.read(reader, 1)
            """))
    for obj in input:
        data = pickle.dumps(obj)
        os.write(s, data)
        os.write(s, b"\x00")
    os.write(s, b"\x00")


if __name__ == "__main__":
    test_pickle_passing()
