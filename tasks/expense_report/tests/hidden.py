import os, sys, subprocess
APP = "src/ledger.py"

def run(args=(), stdin=""):
    return subprocess.run([sys.executable, APP, *list(args)],
                          input=stdin, capture_output=True, text=True)

r = run(['total'], '2026-01-05,food,10.00\n2026-02-03,food,5.005\n2026-01-20,rent,800\n2026-01-15,fun,5.00\n2026-02-10,fun,5.00\n\n2026-02-28,food,-2.50\n')
assert (r.returncode, r.stdout) == (0, '822.51\n'), repr((r.returncode, r.stdout, r.stderr))
r = run(['count'], '2026-01-05,food,10.00\n2026-02-03,food,5.005\n2026-01-20,rent,800\n2026-01-15,fun,5.00\n2026-02-10,fun,5.00\n\n2026-02-28,food,-2.50\n')
assert (r.returncode, r.stdout) == (0, '6\n'), repr((r.returncode, r.stdout, r.stderr))
r = run(['average'], '2026-01-05,food,10.00\n2026-02-03,food,5.005\n2026-01-20,rent,800\n2026-01-15,fun,5.00\n2026-02-10,fun,5.00\n\n2026-02-28,food,-2.50\n')
assert (r.returncode, r.stdout) == (0, '137.08\n'), repr((r.returncode, r.stdout, r.stderr))
r = run(['categories'], '2026-01-05,food,10.00\n2026-02-03,food,5.005\n2026-01-20,rent,800\n2026-01-15,fun,5.00\n2026-02-10,fun,5.00\n\n2026-02-28,food,-2.50\n')
assert (r.returncode, r.stdout) == (0, 'rent: 800.00\nfood: 12.51\nfun: 10.00\n'), repr((r.returncode, r.stdout, r.stderr))
r = run(['top', '2'], '2026-01-05,food,10.00\n2026-02-03,food,5.005\n2026-01-20,rent,800\n2026-01-15,fun,5.00\n2026-02-10,fun,5.00\n\n2026-02-28,food,-2.50\n')
assert (r.returncode, r.stdout) == (0, 'rent: 800.00\nfood: 12.51\n'), repr((r.returncode, r.stdout, r.stderr))
r = run(['top', '9'], '2026-01-05,food,10.00\n2026-02-03,food,5.005\n2026-01-20,rent,800\n2026-01-15,fun,5.00\n2026-02-10,fun,5.00\n\n2026-02-28,food,-2.50\n')
assert (r.returncode, r.stdout) == (0, 'rent: 800.00\nfood: 12.51\nfun: 10.00\n'), repr((r.returncode, r.stdout, r.stderr))
r = run(['category', 'food'], '2026-01-05,food,10.00\n2026-02-03,food,5.005\n2026-01-20,rent,800\n2026-01-15,fun,5.00\n2026-02-10,fun,5.00\n\n2026-02-28,food,-2.50\n')
assert (r.returncode, r.stdout) == (0, '12.51\n'), repr((r.returncode, r.stdout, r.stderr))
r = run(['total'], '')
assert (r.returncode, r.stdout) == (0, '0.00\n'), repr((r.returncode, r.stdout, r.stderr))
r = run(['average'], '')
assert (r.returncode, r.stdout) == (0, '0.00\n'), repr((r.returncode, r.stdout, r.stderr))
r = run(['categories'], '')
assert (r.returncode, r.stdout) == (0, ''), repr((r.returncode, r.stdout, r.stderr))
r = run(['categories'], '2026-01-01,beta,5.00\n2026-01-02,alpha,5.00\n2026-01-03,gamma,9.00\n')
assert (r.returncode, r.stdout) == (0, 'gamma: 9.00\nalpha: 5.00\nbeta: 5.00\n'), repr((r.returncode, r.stdout, r.stderr))
r = run(['category', 'nope'], '2026-01-05,food,10.00\n2026-02-03,food,5.005\n2026-01-20,rent,800\n2026-01-15,fun,5.00\n2026-02-10,fun,5.00\n\n2026-02-28,food,-2.50\n')
assert r.returncode == 1 and r.stdout == "", repr((r.returncode, r.stdout, r.stderr))
r = run(['wat'], '2026-01-05,food,10.00\n2026-02-03,food,5.005\n2026-01-20,rent,800\n2026-01-15,fun,5.00\n2026-02-10,fun,5.00\n\n2026-02-28,food,-2.50\n')
assert r.returncode == 2 and r.stdout == "", repr((r.returncode, r.stdout, r.stderr))
r = run([], '2026-01-05,food,10.00\n2026-02-03,food,5.005\n2026-01-20,rent,800\n2026-01-15,fun,5.00\n2026-02-10,fun,5.00\n\n2026-02-28,food,-2.50\n')
assert r.returncode == 2 and r.stdout == "", repr((r.returncode, r.stdout, r.stderr))
r = run(['total'], 'bad,line\n')
assert r.returncode == 2 and r.stdout == "", repr((r.returncode, r.stdout, r.stderr))

print("ALL TESTS PASSED")
