import os, sys, subprocess
APP = "src/expand.py"

def run(args=(), stdin=""):
    return subprocess.run([sys.executable, APP, *list(args)],
                          input=stdin, capture_output=True, text=True)

r = run([], '1-3,5,7-9\n')
assert (r.returncode, r.stdout) == (0, '1 2 3 5 7 8 9\n'), repr((r.returncode, r.stdout, r.stderr))
r = run([], '5\n')
assert (r.returncode, r.stdout) == (0, '5\n'), repr((r.returncode, r.stdout, r.stderr))
r = run([], '1-1\n')
assert (r.returncode, r.stdout) == (0, '1\n'), repr((r.returncode, r.stdout, r.stderr))
r = run([], '9-7\n')
assert (r.returncode, r.stdout) == (0, '9 8 7\n'), repr((r.returncode, r.stdout, r.stderr))
r = run([], '1-3,5-3\n')
assert (r.returncode, r.stdout) == (0, '1 2 3 5 4 3\n'), repr((r.returncode, r.stdout, r.stderr))
r = run([], '10-12,3-1\n')
assert (r.returncode, r.stdout) == (0, '10 11 12 3 2 1\n'), repr((r.returncode, r.stdout, r.stderr))
r = run([], '\n')
assert (r.returncode, r.stdout) == (0, ''), repr((r.returncode, r.stdout, r.stderr))

print("ALL TESTS PASSED")
