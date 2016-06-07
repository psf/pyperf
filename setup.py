#!/usr/bin/env python3

# Prepare a release:
#
#  - git pull --rebase
#  - update version in setup.py, perf/__init__.py and doc/conf.py
#  - run tests: tox
#  - set release date in the changelog
#  - git commit -a
#  - git push
#
# Release a new version:
#
#  - git tag VERSION
#  - git push --tags
#  - python3 setup.py register sdist bdist_wheel upload
#
# After the release:
#
#  - set version to n+1
#  - git commit -a -m "post-release"
#  - git push

VERSION = '0.3'

DESCRIPTION = 'Python module to generate and modify perf'
CLASSIFIERS = [
    'Development Status :: 4 - Beta',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: MIT License',
    'Natural Language :: English',
    'Operating System :: OS Independent',
    'Programming Language :: Python :: 3',
    'Topic :: Software Development :: Libraries :: Python Modules',
]

# put most of the code inside main() to be able to import setup.py in
# test_tools.py, to ensure that VERSION is the same than
# perf.__version__.
def main():
    try:
        from setuptools import setup
    except ImportError:
        from distutils.core import setup

    with open('README.rst') as fp:
        long_description = fp.read().strip()

    options = {
        'name': 'perf',
        'version': VERSION,
        'license': 'MIT license',
        'description': DESCRIPTION,
        'long_description': long_description,
        'url': 'https://github.com/haypo/perf',
        'author': 'Victor Stinner',
        'author_email': 'victor.stinner@gmail.com',
        'classifiers': CLASSIFIERS,
        'packages': ['perf', 'perf.tests'],
    }
    setup(**options)

if __name__ == '__main__':
    main()
