#! /usr/bin/env python3
from github3 import authorize
from getpass import getpass

user = input('Username: ')
password = ''

while not password:
    password = getpass('Password for {0}: '.format(user))

note = 'Papyros Builder'
note_url = 'http://dash.papyros.io'
scopes = ['user', 'repo']

auth = authorize(user, password, scopes, note, note_url)

with open('.github_auth', 'w') as fd:
    fd.write(auth.token + '\n')
    fd.write(str(auth.id))
