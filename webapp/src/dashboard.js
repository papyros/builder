export class Dashboard {
    repositories = [
        {
            name: 'papyros-testing/x86_64',
            status: 'passed'
        },
        {
            name: 'papyros-testing/i686',
            status: 'failed'
        },
        {
            name: 'papyros/x86_64',
            status: 'running'
        },
        {
            name: 'papyros/i686',
            status: 'queued'
        }
    ];

    statusColor(status) {
        if (status == 'passed')
            return 'green';
        else if (status == 'failed')
            return 'red';
        else if (status == 'queued')
            return 'grey';
        else if (status == 'running')
            return 'yellow';
    }

    statusLabel(status) {
        return status[0].toUpperCase() + status.substring(1)
    }

    viewRepository(repo) {
        console.log(repo)
    }
}
