from pkgbuild.repo import Repository

repo = Repository.from_channel_config('/home/mspencer/Developer/papyros/repository/channels.yml',
        'x86_64', workdir='/home/mspencer/Developer/papyros/repository')
repo.load()
repo.download()
repo.refresh()
repo.build()
