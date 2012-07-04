#!/usr/bin/env python

from fabric.api import *
import os
import re

# What does this release script do:
# get major.minor.micro from setup.py
# Chop off -dev tag at the end. If no dev at the end, bump the micro
# version
# commit it.  
# Tag at the commit.
# Bump to the next dev version: major.minor.micro+1'-dev'
# commit it.
# Push changes and tags to remote

# How do you use a release like this:
# Get it from the GitHub by using the tag + tar ball feature
 
versionTemplates = {
        'release': "version = '%(major)s.%(minor)s.%(micro)s'"
        , 'dev': "version = '%(major)s.%(minor)s.%(micro)s-dev'"
        , 'git-tag': 'v%(major)s.%(minor)s.%(micro)s'
        , 'git-message': 'Release Version %(major)s.%(minor)s.%(micro)s'
        , 'dev-message': 'Bump Version to %(major)s.%(minor)s.%(micro)s-dev'
        }

# Monkey-patch "open" to honor fabric's current directory
_old_open = open
def open(path, *args, **kwargs):
    return _old_open(os.path.join(env.lcwd, path), *args, **kwargs)

def _validateVersion(v):
    versionRe = re.compile('^(?P<major>[0-9]+)\\.(?P<minor>[0-9]+)\\.(?P<micro>[0-9]+)(?P<pre>[-0-9a-zA-Z]+)?$')
    m = versionRe.match(v)
    if not m:
        raise Exception('Version must be in the format <number>.<number>.<number>[<string>]')

    valDict = m.groupdict()
    for k in ('major', 'minor', 'micro'): valDict[k] = int(valDict[k])
    return valDict

# Decorator class to fab target
class _cloneDir(object):
    def __init__(self, gitUrl, project, default_branch):
        self.gitUrl = gitUrl
        self.project = project
        self.default_branch = default_branch

    def __call__(self, f):
        def wrapped_f(*args, **kwargs):
            local('rm -rf ../tmpfab')
            local('mkdir ../tmpfab')
            local('git clone %s ../tmpfab/%s' % (self.gitUrl, self.project))

            with lcd(os.path.join('..', 'tmpfab', self.project)):
                branch = prompt('Please enter release branch:',
                    default=self.default_branch)
                local('git checkout %s' % branch)
                kwargs['branch'] = branch
                f(*args, **kwargs)
            local('rm -rf ../tmpfab')
        return wrapped_f

def _getReleaseVersion():
    # Get current python version
    currentVersionStr = local('python setup.py --version', capture=True).strip()
    
    cvd = _validateVersion(currentVersionStr)
    if not currentVersionStr.endswith('-dev'):
        cvd['micro'] += 1

    nextVersionStr = '%d.%d.%d' % (cvd['major'], cvd['minor'], cvd['micro'])
    print 'You current version is %s.  You release version will be %s' % (currentVersionStr, nextVersionStr)

    return cvd

def _replaceVersionInFile(filename, matchRe, template, versionCb):
    with open(filename, 'r') as rfile:
        lines = rfile.readlines()

    currentVersionStr = None
    for linenum,line in enumerate(lines):
        m = matchRe.search(line)
        if m:
            vals = m.groupdict()
            indent, currentVersionStr, linesep = vals['indent'], vals['version'], line[-1]
            break

    if currentVersionStr is None:
        abort('Version not found in %s.' % (filename))
    version = versionCb(currentVersionStr)
    nextVersionStr = '%s%s%s' % (indent, template % version, linesep)

    lines[linenum] = nextVersionStr
    with open(filename, 'w') as wfile:
        wfile.writelines(lines)

def _gitTag(version, branch='develop'):
    with hide('running', 'stdout', 'stderr'):
        remotes = local('git remote', capture=True).split()
        if len(remotes) == 0:
            abort('You have no configured git remotes.')

    remote = ('origin' if 'origin' in remotes else
              'ooici' if 'ooici' in remotes else
              'ooici-eoi' if 'ooici-eoi' in remotes else
              remotes[0])
    if not remote in remotes:
        abort('"%s" is not a configured remote.' % (remote))

    versionTag = versionTemplates['git-tag'] % version
    versionMsg = versionTemplates['git-message'] % version

    comment = prompt('Optional comment for this release:', default='')
    if comment != '':
        versionMsg += ': ' + comment
    local('git commit -am "%s"' % (versionMsg))
    commit = local('git rev-parse --short HEAD', capture=True)
    local('git tag -af %s -m "%s" %s' % (versionTag, versionMsg, commit))

    print versionTag, versionMsg, commit

    return remote

@_cloneDir(gitUrl='git@github.com:ooici/pyon.git',
    project='pyon',
    default_branch='master')
def release(branch):

    # Deduce release version
    nextVersionD = _getReleaseVersion()
  
    # Update setup.py to release version 
    version_re = re.compile("(?P<indent>\s*)version = '(?P<version>[^\s]+)'")
    _replaceVersionInFile('setup.py', version_re,
            versionTemplates['release'], lambda old: nextVersionD)
    # Tag at release version
    remote = _gitTag(nextVersionD, branch=branch)
   
    # Immediately go to next dev version to ensure release version is tied
    # to one commit only
    nextVersionD['micro'] += 1
    _replaceVersionInFile('setup.py', version_re,
            versionTemplates['dev'], lambda old: nextVersionD)

    devMsg = versionTemplates['dev-message'] % nextVersionD
    local('git commit -am "%s"' % devMsg)

    # Push commits and tags
    local('git push %s --tags' % (remote))
    local('git push %s %s' % (remote, branch))
