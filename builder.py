from pkgbuild.repo import Repository

repo = Repository('papyros', 'x86_64', ['greenisland-git', 'qml-material'],
        workdir='/home/mspencer/Developer/papyros/repository')
repo.load()
repo.download()
