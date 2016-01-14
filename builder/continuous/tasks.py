from builder.chroot import Chroot
from builder.core import celery, gh, logger
from builder.utils import locked


@celery.task(bind=True)
@locked(key="chroot", timeout=60 * 60 * 2)
def build_continuous(self, repo, sha=None, branch=None, patch_url=None):
    chroot = Chroot(repo.name)
    chroot.bind_rw = [repo.workdir + ':/source', '/var/cache/npm:/npm_cache']

    logger.info('Building repo: ' + repo.name)
    logger.info('Fetching sources...')
    repo.source.checkout(sha=sha, branch=branch, patch_url=patch_url)

    config = repo.config

    if not config:
        logger.warn('Repository has no build config: ' + repo.name)
        return

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
def update_commit_status(repo_name, sha, state, description, context):
    repo = gh.repository(*repo_name.split('/'))

    status = repo.create_status(sha=sha, state=state, description=description,
            context=context)
