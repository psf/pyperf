#!/usr/bin/env python3

# Prepare a release:
#
#  - git pull --rebase
#  - update version in setup.py, pyperf/__init__.py and doc/conf.py
#  - set release date in doc/changelog.rst
#  - git commit -a -m "prepare release x.y"
#  - Remove untracked files/dirs: git clean -fdx
#  - run tests: tox --parallel auto
#  - git push or send the PR to the repository
#  - check Github Action CI: https://github.com/psf/pyperf/actions/workflows/build.yml
#
# Release a new version:
#
#  - go to the Github release tab: https://github.com/psf/pyperf/releases
#  - click "Draft a new release" and fill the contents
#  - finally click the "Publish release" button! Done!
#  - monitor the publish status: https://github.com/psf/pyperf/actions/workflows/publish.yml
#
# After the release:
#
#  - set version to n+1
#  - git commit -a -m "post-release"
#  - git push or send the PR to the repository

VERSION = '2.4.0'

DESCRIPTION = 'Python module to run and analyze benchmarks'
CLASSIFIERS = [
    'Development Status :: 5 - Production/Stable',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: MIT License',
    'Natural Language :: English',
    'Operating System :: OS Independent',
    'Programming Language :: Python :: 3',
    'Topic :: Software Development :: Libraries :: Python Modules',
]


# put most of the code inside main() to be able to import setup.py in
# test_tools.py, to ensure that VERSION is the same than
# pyperf.__version__.
def main():
    from setuptools import setup

    with open('README.rst') as fp:
        long_description = fp.read().strip()

    options = {
        'name': 'pyperf',
        'version': VERSION,
        'license': 'MIT license',
        'description': DESCRIPTION,
        'long_description': long_description,
        'url': 'https://github.com/psf/pyperf',
        'author': 'Victor Stinner',
        'author_email': 'vstinner@redhat.com',
        'classifiers': CLASSIFIERS,
        'packages': ['pyperf', 'pyperf.tests'],
        'install_requires': [],
        # don't use environment markers in install_requires, but use weird
        # syntax of extras_require, to support setuptools 18
        'extras_require': {
            ":python_version < '3.4'": ["statistics"],
        },
        'entry_points': {
            'console_scripts': ['pyperf=pyperf.__main__:main']
        }
        # Optional dependencies:
        # 'psutil'
    }
    setup(**options)


if __name__ == '__main__':
    main()
