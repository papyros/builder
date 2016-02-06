export class App {

    configureRouter(config, router) {
        config.title = 'Aurelia';
        config.map([
            {
                route: '', name: 'dashboard', moduleId: 'dashboard',
                nav: true, title:'Dashboard'
            },
            {
                route: 'packages', name: 'packages', moduleId: 'packages',
                nav: true, title:'Packages'
            }
        ]);

        this.router = router;
    }
}
