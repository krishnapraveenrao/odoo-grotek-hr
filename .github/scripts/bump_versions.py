"""Bump the version of every Odoo module changed between two commits.

Odoo.sh upgrades a module on production only when the 'version' in its __manifest__.py
changes. This raises the last number (19.0.1.0.0 -> 19.0.1.0.1) for each module whose files
changed in BEFORE..AFTER, unless the version was already changed in that range.

Usage: python bump_versions.py BEFORE AFTER   (prints the bumped modules, one per line)
"""
import re
import subprocess
import sys
from pathlib import Path

VERSION_RE = re.compile(r"""(['"]version['"]\s*:\s*['"])([\d.]+)(['"])""")


def git(*args):
    return subprocess.run(['git', *args], check=True, capture_output=True, text=True).stdout


def manifest_version(text):
    match = VERSION_RE.search(text or '')
    return match.group(2) if match else None


def version_at(commit, manifest):
    try:
        return manifest_version(git('show', f'{commit}:{manifest}'))
    except subprocess.CalledProcessError:
        return None  # module did not exist at that commit


def main(before, after):
    changed = git('diff', '--name-only', before, after).splitlines()
    modules = sorted({path.split('/')[0] for path in changed if '/' in path})
    bumped = []
    for module in modules:
        manifest = Path(module, '__manifest__.py')
        if not manifest.is_file():
            continue
        old = version_at(before, manifest.as_posix())
        text = manifest.read_text(encoding='utf-8')
        new = manifest_version(text)
        if new is None or old is None or old != new:
            continue  # new module, no version, or already bumped by hand
        parts = new.split('.')
        parts[-1] = str(int(parts[-1]) + 1)
        manifest.write_text(VERSION_RE.sub(rf"\g<1>{'.'.join(parts)}\g<3>", text, count=1), encoding='utf-8')
        bumped.append(f'{module} {new} -> {".".join(parts)}')
    print('\n'.join(bumped))


if __name__ == '__main__':
    main(*sys.argv[1:3])
