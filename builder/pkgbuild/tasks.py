import os.path

from builder.core import celery, gh, logger
from builder.helpers import rsync
from builder.utils import append_to_file, locked, replace_in_file, run


@celery.task(bind=True)
@locked(key="ccm", timeout=60 * 60 * 2)
def build_repository(self, repo, branch):
    logger.info('Fetching repository configuration and PKGBUILDs...')
    repo.source.pull(branch=branch)

    config = repo.config

    if not config:
        logger.error('Repository configuration not found: ' + repo.name)
        return

    logger.info('Loading configuration...')
    config.load()

    logger.info('Downloading package sources...')
    config.download()

    logger.info('Loading package information...')
    config.refresh()

    logger.info('Building packages...')
    if os.path.exists(config.repo_dir):
        rmtree(config.repo_dir)
    for package in self.repo.packages:
        self.status = 'Building {}'.format(package.name)
        package.build()

    logger.info('Saving build information...')
    for package in config.packages:
        config.buildinfo.get('packages')[package.name] = package.gitrev
    config.buildinfo['build_number'] = config.build_number
    save_yaml(os.path.join(config.workdir, 'buildinfo.yml'), config.buildinfo)

    logger.info('Committing build information...')
    repo.source.index.add(['buildinfo.yml'] +
                   ['packages/{}/PKGBUILD'.format(pkg.name) for pkg in config.packages])
    repo.source.index.commit('Build {} at {:%c}\n\n{}'.format(config.build_number, datetime.now(),
                                                       config.changelog),
                      author=Actor("Builder", "builder@papyros.io"))
    repo.source.remotes.origin.push()

    logger.info('Exporting built packages...')
    rsync(config.repo_dir, export_dir, sudo=True)
