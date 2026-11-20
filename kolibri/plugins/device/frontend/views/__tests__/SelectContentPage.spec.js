import { nextTick } from 'vue';
import { render, screen, fireEvent } from '@testing-library/vue';
import TaskResource from 'kolibri/apiResources/TaskResource';
import plugin_data from 'kolibri-plugin-data';
import { createTranslator, i18nSetup } from 'kolibri/utils/i18n';
import bytesForHumans from 'kolibri/uiText/bytesForHumans';
import SelectContentPage, { pageTitleStrings } from '../SelectContentPage';
import pluginStore from '../../store';
import {
  makeSelectContentPageStore,
  selectContentTransferredChannel,
} from '../../__tests__/utils/makeStore';
import ChannelContentsSummary from '../SelectContentPage/ChannelContentsSummary';
import ContentTreeViewer from '../SelectContentPage/ContentTreeViewer';
import NewChannelVersionBanner from '../ManageContentPage/NewChannelVersionBanner';
import SelectionBottomBar from '../ManageContentPage/SelectionBottomBar';
import router from './testRouter';

jest.mock('kolibri/apiResources/TaskResource');
jest.mock('kolibri-plugin-data', () => ({}));

const pageTr = createTranslator('SelectContentPage', SelectContentPage.$trs);
const summaryTr = createTranslator('ChannelContentsSummary', ChannelContentsSummary.$trs);
const bannerTr = createTranslator('NewChannelVersionBanner', NewChannelVersionBanner.$trs);
const treeViewerTr = createTranslator('ContentTreeViewer', ContentTreeViewer.$trs);
const bottomBarTr = createTranslator('SelectionBottomBar', SelectionBottomBar.$trs);

function renderComponent(options) {
  const { store, props = {} } = options;
  return render(SelectContentPage, {
    props,
    store: store || makeSelectContentPageStore(),
    ...router,
  });
}

function updateMetaChannel(store, updates) {
  const { transferredChannel } = store.state.manageContent.wizard;
  store.commit('manageContent/wizard/SET_TRANSFERRED_CHANNEL', {
    ...transferredChannel,
    ...updates,
  });
}

describe('SelectContentPage', () => {
  let store;

  beforeAll(async () => {
    await i18nSetup(true);
  });

  beforeEach(() => {
    store = makeSelectContentPageStore();
  });

  it('titles the tab with the channel name, with the channel name the only h1', async () => {
    document.title = '';
    const { name } = selectContentTransferredChannel;
    pluginStore.replaceState(store.state);
    renderComponent({ store: pluginStore });
    await nextTick();
    expect(document.title).toBe(
      `${pageTitleStrings.selectContent$({ channelName: name })} - Kolibri`,
    );
    const headings = screen.queryAllByRole('heading', { level: 1 });
    expect(headings).toHaveLength(1);
    expect(headings[0]).toHaveTextContent(name);
  });

  it('shows the thumbnail, title, descripton, and version of the channel', () => {
    const { name, version, description } = selectContentTransferredChannel;
    const fakeImage = 'data:image/png;base64,abcd1234';
    updateMetaChannel(store, { thumbnail: fakeImage });
    renderComponent({ store });
    expect(screen.getByRole('img')).toHaveAttribute('src', fakeImage);
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(name);
    expect(screen.getByText(summaryTr.$tr('version', { version }))).toBeInTheDocument();
    expect(screen.getByText(description)).toBeInTheDocument();
  });

  it('shows the total size of the channel', () => {
    const { total_resources, total_file_size } = selectContentTransferredChannel;
    renderComponent({ store });
    expect(screen.getAllByRole('row')[1]).toHaveTextContent(
      `${summaryTr.$tr('totalSizeRow')} ${total_resources.toLocaleString()} ${bytesForHumans(total_file_size)}`,
    );
  });

  it('shows the total size of any resources on the device', () => {
    const { on_device_resources, on_device_file_size } = selectContentTransferredChannel;
    renderComponent({ store });
    expect(screen.getAllByRole('row')[2]).toHaveTextContent(
      `${summaryTr.$tr('onDeviceRow')} ${on_device_resources.toLocaleString()} ${bytesForHumans(on_device_file_size)}`,
    );
  });

  it('shows size and resources as 0 if channel is not on device', () => {
    const onDeviceResources = 0;
    const onDeviceFileSize = 0;
    updateMetaChannel(store, {
      id: 'not_awesome_channel',
      on_device_resources: onDeviceResources,
      on_device_file_size: onDeviceFileSize,
    });
    renderComponent({ store });
    expect(screen.getAllByRole('row')[2]).toHaveTextContent(
      `${summaryTr.$tr('onDeviceRow')} ${onDeviceResources.toLocaleString()} ${bytesForHumans(onDeviceFileSize)}`,
    );
  });

  it('shows a update notification if a new version is available', () => {
    const newVersion = 1000;
    updateMetaChannel(store, { version: newVersion });
    renderComponent({ store });
    expect(
      screen.getByText(bannerTr.$tr('versionAvailable', { version: newVersion })),
    ).toBeInTheDocument();
  });

  it('if a new version is not available, then no notification/button appear', () => {
    const { version } = selectContentTransferredChannel;
    updateMetaChannel(store, { version });
    renderComponent({ store });
    expect(
      screen.queryByText(bannerTr.$tr('versionAvailable', { version })),
    ).not.toBeInTheDocument();
  });

  describe('draft channel (installed version = 0)', () => {
    const newerVersion = 15;

    function setInstalledVersion(store, version) {
      const existing = store.state.manageContent.channelList[0];
      store.commit('manageContent/SET_CHANNEL_LIST', [{ ...existing, version }]);
    }

    it('shows ContentTreeViewer when installed version is 0 and Studio has newer version', () => {
      setInstalledVersion(store, 0);
      updateMetaChannel(store, { version: newerVersion });
      renderComponent({ store });
      expect(
        screen.getByRole('checkbox', {
          name: treeViewerTr.$tr('selectAll'),
        }),
      ).toBeInTheDocument();
    });

    it('shows NewChannelVersionBanner when installed version is 0 and Studio has newer version', () => {
      setInstalledVersion(store, 0);
      updateMetaChannel(store, { version: newerVersion });
      renderComponent({ store });
      expect(
        screen.getByText(bannerTr.$tr('versionAvailable', { version: newerVersion })),
      ).toBeInTheDocument();
    });

    it('shows SelectionBottomBar when installed version is 0 and Studio has newer version', () => {
      setInstalledVersion(store, 0);
      updateMetaChannel(store, { version: newerVersion });
      renderComponent({ store });
      expect(
        screen.getByRole('button', { name: bottomBarTr.$tr('importAction') }),
      ).toBeInTheDocument();
    });

    it('hides ContentTreeViewer when installed version > 0 and newer version available on Studio', () => {
      updateMetaChannel(store, { version: 1000 });
      renderComponent({ store });
      expect(
        screen.queryByRole('checkbox', {
          name: treeViewerTr.$tr('selectAll'),
        }),
      ).not.toBeInTheDocument();
    });
  });

  describe('playing videos from YouTube', () => {
    afterEach(() => {
      delete plugin_data.canStreamVideos;
    });

    // The checkbox's description is part of its name
    const streamVideosName = name => name.startsWith(pageTr.$tr('streamVideos'));

    function streamVideosCheckbox() {
      return screen.queryByRole('checkbox', { name: streamVideosName });
    }

    function selectResources() {
      Object.assign(store.state.manageContent.wizard, {
        selectedDrive: { id: 'a-drive', name: 'A drive' },
        transferResourceCount: 3,
      });
    }

    it("isn't offered when videos can't play from YouTube", () => {
      renderComponent({ store });
      expect(streamVideosCheckbox()).not.toBeInTheDocument();
    });

    it("starts an import that leaves out videos' files when asked to", async () => {
      plugin_data.canStreamVideos = true;
      // Left pending: the page would go on to the task list
      TaskResource.startTask.mockReturnValue(new Promise(() => {}));
      selectResources();
      renderComponent({ store });

      await fireEvent.click(streamVideosCheckbox());
      await fireEvent.click(screen.getByRole('button', { name: bottomBarTr.$tr('importAction') }));

      expect(TaskResource.startTask).toHaveBeenCalledWith(
        expect.objectContaining({ drive_id: 'a-drive', stream: true }),
      );
    });

    it("downloads videos' files unless asked not to", async () => {
      plugin_data.canStreamVideos = true;
      // Left pending: the page would go on to the task list
      TaskResource.startTask.mockReturnValue(new Promise(() => {}));
      selectResources();
      renderComponent({ store });

      await fireEvent.click(screen.getByRole('button', { name: bottomBarTr.$tr('importAction') }));

      expect(TaskResource.startTask).toHaveBeenCalledWith(
        expect.not.objectContaining({ stream: expect.anything() }),
      );
    });
  });
});
