from test.support import interpreters


def test_run_script():
    interp = interpreters.create()
    main_script = "a_module.py"
    interp.run(f"import runpy; runpy.run_path({main_script!r})")

if __name__ == "__main__":
    test_run_script()
