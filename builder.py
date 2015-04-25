import json
import os.path
from enum import Enum
import types
import networkx as nx

class Status:
    SUCCESS='success'
    FAIL='fail'
    WAITING='waiting'
    BUILDING='building'
    NOT_BUILT='not built'

class persist(object):
    
    def __init__(self, name, default=None, doc=None):
        self.name = name
        self.default = default
        self.__doc__ = doc

    def __get__(self, obj, objtype):
        if obj is None:
            return self
        return obj._get(self.name, self.default)

    def __set__(self, obj, value):
        obj._set(self.name, value)

    def __delete__(self, obj):
        raise AttributeError('Can\'t delete attribute')

class PersistentObject:
    info = None

    def __init__(self, path):
        self.path = path

        if os.path.exists(path + '/info.json'):
            with open(path + '/info.json') as f:
                self.info = json.load(f)
        else:
            self.info = {}

    def _set(self, key, value):
        self.info[key] = value

        with open(self.path + '/info.json', 'w') as f:
            json.dump(self.info, f)

    def _get(self, key, default_value=None):
        if key in self.info:
            return self.info[key]
        else:
            print(default_value)
            return default_value

class Container(PersistentObject):
    latest_build_number = persist('latest_build_number', 0)

    def build(self, version):
        self.latest_build_number += 1

        return Build(self, self.latest_build_number, version)
        
    def unsorted_jobs(self):
        return []

    def jobs(self):
        unsorted_jobs = self.unsorted_jobs()
        job_names = [job.name for job in unsorted_jobs]
        jobs = []

        graph = nx.DiGraph()
        roots = set()

        for job in unsorted_jobs:
            if len(job.depends()) == 0:
                roots.add(job.name)
            else:
                for dependency in job.depends():
                    graph.add_edge(dependency, job.name)

        for job_name in roots:
            jobs.append(unsorted_jobs[job_names.index(job_name)])
            if job_name in graph.nodes():
                for predep, dep in nx.dfs_edges(graph, job_name):
                    jobs.append(unsorted_jobs[job_names.index(dep)])

        return jobs

    def get_job(self, name):
        for job in self.jobs:
            if job.name == name:
                return job

        return None


class Build:
    status = Status.BUILDING
    number = 0
    version = "v0.0.0"

    def __init__(self, container, number, version):
        self.number = number
        self.version = version
        self.container = container
        self.jobs = container.jobs()

    def execute(self):
        status = Status.SUCCESS

        for job in self.jobs:
            print(job.summary())

        for job in self.jobs:
            # TODO: Automatically fail a job if its dependencies failed
            if job.needs_build(self.container):
                print('>>> Building ' + job.name)
                job.execute()

                if job.status == Status.FAIL:
                    status = Status.FAIL
                print('\n--> ' + job.status + '\n')
            else:
                print('=== Skipping ' + job.name + ' (already built)\n')

        self.status = status

        print('=== Build complete: ' + str(status))

        return status


class Job(PersistentObject):
    name = ""
    log = persist('log')
    status = persist('status', Status.NOT_BUILT)

    def __init__(self, path):
        super().__init__(path)

    def execute(self):
        self.status = Status.SUCCESS
    def summary(self):
        return '{name:49} {status}'.format(
                name=self.name,
                status=self.status)

    def artifacts(self): pass
    def depends(self): return []

    def needs_build(self, container):
        if self.status != Status.SUCCESS:
            return True

        for dep in self.depends():
            job = container.get_job(dep)
            if not job.needs_build():
                return True

        return False