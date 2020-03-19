#!/usr/bin/env python3

# Prepare a release:
#
#  - git pull --rebase
#  - update version in setup.py, pyperf/__init__.py and doc/conf.py
#  - set release date in doc/changelog.rst
#  - git commit -a -m "prepare release x.y"
#  - Remove untracked files/dirs: git clean -fdx
#  - run tests: tox --parallel auto
#  - git push
#  - check Travis CI status:
#    https://travis-ci.org/vstinner/pyperf
#
# Release a new version:
#
#  - git tag VERSION
#  - git clean -fdx  # Remove untracked files/dirs
#  - python3 setup.py sdist bdist_wheel
#  - git push --tags
#  - twine upload dist/*
#
# After the release:
#
#  - set version to n+1
#  - git commit -a -m "post-release"
#  - git push

VERSION = '2.0.1'

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
        'url': 'https://github.com/vstinner/pyperf',
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
