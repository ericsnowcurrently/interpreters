import os
import textwrap as tw
from test.support import interpreters

ISSUE = "hangs"

def test_share_file_descriptor():
    print(ISSUE); return
    interp = interpreters.create()
    r1, s1 = os.pipe()
    r2, s2 = os.pipe()
    interp.run(tw.dedent(f"""
            import os
            fd = int.from_bytes(
                    os.read({r1}, 10), 'big')
            for line in os.fdopen(fd):
                print(line)
            os.write({s2}, b'')
            """))
    with open('spamspamspam') as infile:
        fd = infile.fileno().to_bytes(1, 'big')
        os.write(s1, fd)
        os.read(r2, 1)


if __name__ == "__main__":
    test_share_file_descriptor()
