import heartbeat from 'kolibri/heartbeat';
import router from 'kolibri/router';
import urls from 'kolibri/urls';
import { setRequestAdapter } from 'kolibri/utils/baseClient';
import KolibriApp from 'kolibri-app';
import plugin_data from 'kolibri-plugin-data';
import RootVue from '../../learn/frontend/views/LearnIndex';
import routes from '../../learn/frontend/routes';
import store from '../../learn/frontend/store';
import { prepareLearnApp } from '../../learn/frontend/composables/useCoreLearn';
import createLibraryAdapter from './libraryAdapter';

// There is no Kolibri server behind this page: the library's files answer its requests
setRequestAdapter(createLibraryAdapter(plugin_data.libraryDataUrl));

// A static host serves the unzipped archives from the page's own origin, the only
// one it has, rather than from Kolibri's separate zip content origin
Object.defineProperties(urls, {
  __zipContentOrigin: { value: '' },
  __zipContentPort: { value: '' },
});

/*
 * Learn's library, topic and resource pages, as a guest sees them.
 */
class StaticLibraryModule extends KolibriApp {
  get routes() {
    return routes;
  }
  get RootVue() {
    return { ...RootVue, store };
  }
  startRootVue() {
    // Kolibri's core checks the session as soon as it loads, before this module
    // answers requests, so the static host answered that check: ask again here
    return heartbeat
      .pollSessionEndPoint()
      .then(prepareLearnApp)
      .then(() => super.startRootVue());
  }
  ready() {
    // As in Learn: after every navigation, block double-clicks
    router.afterEach((toRoute, fromRoute) => {
      store.dispatch('resetModuleState', { toRoute, fromRoute });
    });
    super.ready();
  }
}

export default new StaticLibraryModule();
