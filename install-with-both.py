#!/usr/bin/env python3
"""Discover discrepancies in current and alpha pip dependency resolver behavior

Run against a repo to discover requirements files and record ``install`` and
``freeze`` results.

See output_dir to customize output location.
"""

import hashlib
import os
import os.path
import re
import shutil
import subprocess
import sys


output_dir = os.environ['HOME'] + '/tmp/test-pip-alpha-resolver'
pyversion = '3.5'
pip_version = '20.2b1'
re_req_file = re.compile(r'requirements[^\s]*\.txt')
resolver_args = {
    'main': (),
    'alpha': ('--unstable-feature=resolver',)
}

def main(repo_path):
    repo_path = repo_path.rstrip('/')
    for combo in discover_requirements_paths(repo_path):
        # TODO: Use exit code and a diff of the freeze files to see if
        # we can delete the venvs.
        run_repo_combo(repo_path, combo, 'main')
        run_repo_combo(repo_path, combo, 'alpha')

def discover_requirements_paths(repo_path):
    """
    Returns a set of tuples, each tuple being a collection of relative paths at
    which there seems to be a requirements file.
    
    Written with edX's dependency management in mind. Probably lots of false
    positives and false negatives, too.
    """
    invocations = set()
    try:
        with open(repo_path + '/Makefile') as f:
            for line in f:
                if 'pip-sync' in line or 'pip install' in line:
                    invocations.add(tuple(sorted(re_req_file.findall(line))))
    except:
        pass
    # Not every repo has a `make requirements` target, so try to
    # find the best target by sniffing in the requirements dir:
    plausible = ['requirements/%s.txt' % s for s in ['dev', 'development', 'base']]
    plausible += ['requirements%s.txt' % s for s in ['', '-dev']]
    for req_path in plausible:
        if os.path.isfile('%s/%s' % (repo_path, req_path)):
            invocations.add((req_path,))
            break
    # Remove any empty invocations
    invocations.discard(())
    return invocations

def run_repo_combo(repo_path, req_combo, resolver):
    """
    Run dependency resolution on a repo using the given tuple of requirements
    paths and the specified resolver (main or alpha). Return True if no
    process failures.
    """
    # Deterministic input to hash -- things that can't be in the path
    id_text = '%s-%s' % (repo_path, req_combo)
    # A unique, deterministic ID for this run
    inst_id = hashlib.sha256(id_text.encode()).hexdigest()[:16]
    
    # Progress information
    print('===== %s %s via %s / %s =====' % (repo_path, req_combo, resolver, inst_id))
    
    base = '%s/%s/%s-%s-%s' % (output_dir, inst_id, pyversion, pip_version, resolver)
    if shutil.rmtree.avoids_symlink_attacks and os.path.isdir(base):
        shutil.rmtree(base)
    os.makedirs(base)
    with open(base + '/info.txt', 'w') as f:
        info_text = 'd: %s\ni: %s\nr: %s\nv: %s\np: %s\n' % (repo_path, req_combo, resolver, pyversion, pip_version)
        f.write(info_text)

    failure = False

    # Create a virtualenv
    venv = base + '/venv'
    pip = venv + '/bin/pip'
    p = subprocess.run(['virtualenv', '-q', '-p', 'python' + pyversion, venv])
    if p.returncode is not 0:
        return False
    p = subprocess.run([pip, 'install', '-q', 'pip==' + pip_version])
    if p.returncode is not 0:
        return False

    # Run pip install
    pip_cmd_base = [pip, 'install', *resolver_args[resolver]]
    req_args = [a for f in req_combo for a in ['-r', f]] # silly
    with open(base + '/install_out.txt', 'w') as out_f:
        with open(base + '/install_err.txt', 'w') as err_f:
            p = subprocess.run(pip_cmd_base + req_args, cwd=repo_path, timeout=600, stdout=out_f, stderr=err_f)
            with open(base + '/install.exit', 'w') as exit_f:
                failure |= bool(p.returncode)
                exit_f.write(str(p.returncode))

    # Run pip freeze
    with open(base + '/freeze_out.txt', 'w') as out_f:
        with open(base + '/freeze_err.txt', 'w') as err_f:
            p = subprocess.run([pip, 'list', '--format=freeze'], cwd=repo_path, timeout=60, stdout=out_f, stderr=err_f)
            with open(base + '/freeze.exit', 'w') as exit_f:
                failure |= bool(p.returncode)
                exit_f.write(str(p.returncode))

    return not failure

if __name__ == '__main__':
    main(*sys.argv[1:])
