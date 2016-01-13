from builder.chroot import Chroot
from builder.core import celery, gh, logger


@celery.task
def build_continuous(repo, patch_url=None, branch=None):
    chroot = Chroot(repo.name)
    chroot.bind_rw = [repo.workdir + ':/source', '/var/cache/npm:/npm_cache']

    logger.info('Building repo: ' + repo.name)
    logger.info('Fetching sources...')
    repo.source.pull(branch)

    if patch_url is not None:
        logger.info("Applying patch...")
        repo.source.patch(patch_url)

    config = repo.config

    logger.info('Creating chroot...')
    chroot.create()

    logger.info('Installing dependencies...')
    chroot.install(config.get('dependencies', []))

    if 'npm-dependencies' in config:
        logger.info('Installing NPM dependencies globally...')
        chroot.install(['npm'])
        chroot.run(['npm', 'install', '-g'] + config['npm-dependencies'])

    logger.info("Copying source directory...")
    chroot.run(['cp', '-r', '/source', '/build'])

    logger.info('Running build steps...')
    for cmd in config.get('build', []):
        logger.info('--> ' + cmd)
        chroot.run(cmd.format(srcdir='/build'), workdir='/build')

    logger.info('Repository passed continuous integration: ' + repo.name)


@celery.task
def update_commit_status(repo_name, sha, state, description):
    repo = gh.repository(repo_name)

    status = repository.create_status(sha=sha, state=state, description=description,
                                      context='continuous-integration/builder')
