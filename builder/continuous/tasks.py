from builder.core import celery, logger, gh
from builder.chroot import Chroot

@celery.task
def build_continuous(repo, sha=None):
    chroot = Chroot(repo.name)
    chroot.bind_ro = [repo.workdir + ':/source']

    config = repo.config

    logger.info('Building repo: ' + repo.name)
    logger.info('Fetching sources...')
    if not repo.source.pull(sha):
        logger.info("No updates, not building")
        return

    logger.info('Creating chroot...')
    chroot.create()

    logger.info('Installing dependencies...')
    chroot.run(['mkdir', '/build'])
    chroot.install(config.get('dependencies', []))

    logger.info('Running build steps...')
    for cmd in config.get('build', []):
        logger.info('--> ' + cmd)
        cmd = 'cd /build &&' + cmd.format(srcdir='/source')
        chroot.run(['bash', '-c', cmd])

    logger.info('Repository passed continuous integration: ' + repo.name)


@celery.task
def update_commit_status(repo_name, sha, state, description):
    repo = gh.repository(repo_name)

    status = repository.create_status(sha=sha, state=state, description=description,
            context='continuous-integration/builder')
