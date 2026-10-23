"""Bump the version of every Odoo module changed between two commits.

Odoo.sh upgrades a module on production only when the 'version' in its __manifest__.py
changes. This raises the last number (19.0.1.0.0 -> 19.0.1.0.1) for each module whose files
changed in BEFORE..AFTER, unless the version was already changed in that range.

Usage: python bump_versions.py BEFORE AFTER   (prints the bumped modules, one per line)
       python bump_versions.py --resolve      (during a merge: settle conflicts that are only in
                                               manifests; exit 1 if any other conflict remains)
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


def as_tuple(version):
    return tuple(int(part) for part in version.split('.'))


def resolve():
    """Take the incoming manifest, keeping the version above both sides.

    Both sides change the version line when the team bumps by hand in qltc-in after a bump
    here. The incoming file wins; if its version is not above ours, ours plus one is used.
    """
    conflicted = git('diff', '--name-only', '--diff-filter=U').splitlines()
    if not conflicted or any(not path.endswith('/__manifest__.py') for path in conflicted):
        return 1
    for path in conflicted:
        ours, theirs = git('show', f':2:{path}'), git('show', f':3:{path}')
        ours_v, theirs_v = manifest_version(ours), manifest_version(theirs)
        if ours_v is None or theirs_v is None:
            return 1
        if as_tuple(theirs_v) <= as_tuple(ours_v):
            parts = ours_v.split('.')
            parts[-1] = str(int(parts[-1]) + 1)
            theirs = VERSION_RE.sub(rf"\g<1>{'.'.join(parts)}\g<3>", theirs, count=1)
        Path(path).write_text(theirs, encoding='utf-8')
        git('add', path)
        print(f'{path}: version {ours_v} (here) / {theirs_v} (qltc-in) -> {manifest_version(theirs)}')
    return 0


if __name__ == '__main__':
    if sys.argv[1:2] == ['--resolve']:
        sys.exit(resolve())
    main(*sys.argv[1:3])
