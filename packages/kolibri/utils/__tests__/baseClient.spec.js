import clientFactory, { setRequestAdapter } from '../baseClient';

describe('baseClient', () => {
  afterEach(() => {
    setRequestAdapter(null);
  });

  it('answers requests from a client made before the adapter was set', async () => {
    const client = clientFactory();
    setRequestAdapter(config =>
      Promise.resolve({ data: { url: config.url, params: config.params }, status: 200, config }),
    );

    const response = await client.get('/api/content/channel/', { params: { available: true } });

    expect(response.data).toEqual({ url: '/api/content/channel/', params: { available: true } });
  });

  it('gives errors without a response a status of 0', async () => {
    const client = clientFactory();
    setRequestAdapter(() => Promise.reject(new Error('Unreachable')));

    await expect(client.get('/api/content/channel/')).rejects.toMatchObject({
      response: { status: 0 },
    });
  });
});
