from builder.core import celery, gh, logger
from builder.utils import locked, run, replace_in_file, append_to_file
from builder.helpers import rsync


@celery.task
@locked(key="iso", timeout=60 * 60 * 2)
def build_iso(iso, branch):
    logger.info('Fetching ISO configuration...')
    iso.source.checkout(branch=branch)

    config = iso.config

    if not config:
        logger.error('ISO configuration not found: ' + iso.name)
        return

    logger.info('Setting up the build directory...')
    rsync('/usr/share/archiso/configs/releng', config.workdir)

    logger.info('Preparing ISO configuration...')

    # Add any additional repos
    replace_in_file(config.path('pacman.conf'), r'\#\[testing\]',
                    '\n\n'.join(config.custom_repos) + '\n\n#[testing]')

    # Add the requested packages
    append_to_file(config.path('packages.both'), config.packages)
    append_to_file(config.path('packages.i686'), config.packages_i686)
    append_to_file(config.path('packages.x86_64'), config.packages_x86_64)

    # Add customizations
    append_to_file(config.path('airootfs/root/customize_airootfs.sh'), config.customizations)

    if config.graphical_target:
        replace_in_file(config.path('airootfs/root/customize_airootfs.sh'),
                        r'multi-user.target', 'graphical.target')

    logger.info('Building ISO...')
    cmd = [config.path('build.sh'), '-v']

    if config.name:
        cmd += ['-N ' + config.name]
    if config.version:
        cmd += ['-V ' + config.version]
    if config.label:
        cmd += ['-L ' + config.label]

    run(cmd, capture_stdout=False, sudo=True, workdir=config.workdir)
