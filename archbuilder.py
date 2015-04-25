#! /usr/bin/env python3

from builder import *
import json
import subprocess, sys

exe_name = sys.argv[0]
exe = os.path.realpath(exe_name)
root_dir = os.path.dirname(exe)

class Channel(Container):
    def __init__(self, name):
        super().__init__(root_dir + '/channels/' + name)
        self.name = name
        with open(root_dir + '/channels/' + name + '/channel.json') as f:
            self.channel = json.load(f)

    def unsorted_jobs(self):
        jobs = []

        for pkgname in os.listdir(self.path + '/packages'):
            if os.path.isdir(self.path + '/packages/' + pkgname):
                jobs.append(PackageJob(self, pkgname))

        return jobs

class PackageJob(Job):
    def __init__(self, channel, name):
        super().__init__(channel.path + '/packages/' + name)
        self.channel = channel
        self.name = name

    def depends(self):
        os.chdir(self.path)
        depends = subprocess.check_output([root_dir + '/pkgdeps']).decode("utf-8")
        depends = [dep.strip() for dep in depends.split(' ')]

        job_depends = []

        for depend in depends:
            if os.path.exists(self.channel.path + '/' + depend):
                job_depends.append(depend)

        return job_depends

    def needs_build(self, container):
        os.chdir(self.path)
        current_version = subprocess.check_output([root_dir + '/pkgver']).decode("utf-8")
        latest_version = subprocess.check_output([root_dir + '/pkgver', '--latest']).decode("utf-8")
        
        print(current_version + ' ?= ' + latest_version)

        return current_version != latest_version or super().needs_build(container)

    def execute(self):
        os.chdir(self.path)
        status = subprocess.call(['extra-x86_64-build']).decode("utf-8")

        if status == 0:
            self.status = Status.SUCCESS
        else:
            self.status = Status.FAIL

    def summary(self):
        os.chdir(self.path)
        current_version = subprocess.check_output([root_dir + '/pkgver']).decode("utf-8").strip()
        latest_version = subprocess.check_output([root_dir + '/pkgver', '--latest']).decode("utf-8").strip()

        version_summary = 'not built' if current_version == '?' else 'v' + current_version

        if latest_version != current_version:
            version_summary += ' -> v' + latest_version

        return '{name:24} {version:24} {status}'.format(
                name=self.name,
                version=version_summary,
                status=self.status)

    def __str__(self):
        return 'pkg/' + self.name

    def __repr__(self):
        return '<archbuilder.PackageJob for ' + self.name + '>'