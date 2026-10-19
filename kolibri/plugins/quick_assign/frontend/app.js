import KolibriApp from 'kolibri-app';
import routes from './routes';

class QuickAssignModule extends KolibriApp {
  get routes() {
    return routes;
  }
}

export default new QuickAssignModule();
