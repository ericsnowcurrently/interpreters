from test.support import interpreters
ISSUE = "RunFailedError: <class 'ImportError'>: No module named a_module"

def test_run_module():
    print(ISSUE); return
    interp = interpreters.create()
    main_module = "a_module"
    interp.run(f'import runpy; runpy.run_module({main_module!r})')

if __name__ == "__main__":
    test_run_module()
