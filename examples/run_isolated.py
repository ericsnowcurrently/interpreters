from test.support import interpreters

def test_run_isolated():
    interp = interpreters.create()
    print('before')
    interp.run('print("during")')
    print('after')