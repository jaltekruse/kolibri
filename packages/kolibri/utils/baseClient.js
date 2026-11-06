/*
 * Internal module that is used by the default client, http client, and
 * the session fetching apparatus. Made as a separate module to avoid
 * circular dependencies and repeated code.
 */
import axios from 'axios';
import qs from 'qs';

let requestAdapter = null;

/*
 * Answers every client's requests with the passed axios adapter instead of sending
 * them over the network, as a page does when there is no Kolibri server behind it.
 * Clients made before the call use it too. Pass null to send requests again.
 */
export function setRequestAdapter(adapter) {
  requestAdapter = adapter;
}

function adapter(config) {
  return (requestAdapter || axios.getAdapter(axios.defaults.adapter, config))(config);
}

export default function clientFactory(options) {
  const client = axios.create({
    adapter,
    xsrfCookieName: 'kolibri_csrftoken',
    xsrfHeaderName: 'X-CSRFToken',
    paramsSerializer: {
      serialize: function (params) {
        // Do custom querystring stingifying to comma separate array params
        return qs.stringify(params, { arrayFormat: 'comma' });
      },
    },
    ...options,
  });
  client.interceptors.response.use(
    response => response,
    function (error) {
      if (!error) {
        error = {};
      }
      if (!error.response) {
        error.response = {
          status: 0,
        };
      }
      return Promise.reject(error);
    },
  );
  return client;
}
