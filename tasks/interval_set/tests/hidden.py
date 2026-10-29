import os, sys, subprocess
APP = "src/intervals.py"

def run(args=(), stdin=""):
    return subprocess.run([sys.executable, APP, *list(args)],
                          input=stdin, capture_output=True, text=True)

r = run(['merge'], '0 2.675\n5 6\n')
assert (r.returncode, r.stdout) == (0, '0 2.675\n5 6\n'), repr((r.returncode, r.stdout, r.stderr))
r = run(['count'], '0 2.675\n5 6\n')
assert (r.returncode, r.stdout) == (0, '2\n'), repr((r.returncode, r.stdout, r.stderr))
r = run(['length'], '0 2.675\n5 6\n')
assert (r.returncode, r.stdout) == (0, '3.68\n'), repr((r.returncode, r.stdout, r.stderr))
r = run(['covers', '2'], '0 2.675\n5 6\n')
assert (r.returncode, r.stdout) == (0, 'yes\n'), repr((r.returncode, r.stdout, r.stderr))
r = run(['covers', '4'], '0 2.675\n5 6\n')
assert (r.returncode, r.stdout) == (0, 'no\n'), repr((r.returncode, r.stdout, r.stderr))
r = run(['merge'], '1.5 3.5\n3.5 4.0\n')
assert (r.returncode, r.stdout) == (0, '1.5 4\n'), repr((r.returncode, r.stdout, r.stderr))
r = run(['length'], '0 1.005\n')
assert (r.returncode, r.stdout) == (0, '1.01\n'), repr((r.returncode, r.stdout, r.stderr))
r = run(['merge'], '')
assert (r.returncode, r.stdout) == (0, ''), repr((r.returncode, r.stdout, r.stderr))
r = run(['length'], '')
assert (r.returncode, r.stdout) == (0, '0.00\n'), repr((r.returncode, r.stdout, r.stderr))
r = run(['wat'], '0 2.675\n5 6\n')
assert r.returncode == 2 and r.stdout == "", repr((r.returncode, r.stdout, r.stderr))
r = run([], '0 2.675\n5 6\n')
assert r.returncode == 2 and r.stdout == "", repr((r.returncode, r.stdout, r.stderr))
r = run(['merge'], '5 1\n')
assert r.returncode == 2 and r.stdout == "", repr((r.returncode, r.stdout, r.stderr))
r = run(['merge'], 'a b\n')
assert r.returncode == 2 and r.stdout == "", repr((r.returncode, r.stdout, r.stderr))

print("ALL TESTS PASSED")
