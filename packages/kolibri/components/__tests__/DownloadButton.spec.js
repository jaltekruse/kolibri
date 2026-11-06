import Vue from 'vue';
import { render, screen } from '@testing-library/vue';
import kolibri from 'kolibri';
import DownloadButton from '../DownloadButton';

jest.mock('kolibri');

const getDownloadableFile = (isExercise = false) => {
  const PRESET = isExercise ? 'exercise' : 'thumbnail';

  // Mock the preset viewer component so that the file is considered renderable
  kolibri.presetViewerComponent = jest
    .fn()
    .mockImplementation(preset => (preset === PRESET ? { template: '<div></div>' } : null));

  return {
    preset: PRESET,
    available: true,
    file_size: 100,
    storage_url: 'http://example.com/sample.png',
    extension: 'png',
    checksum: '1234567890',
  };
};

const renderComponent = props =>
  render(DownloadButton, {
    props: {
      files: [],
      nodeTitle: '',
      ...props,
    },
  });

const SAVE_BUTTON_TEXT = 'Save to device';

describe('DownloadButton', () => {
  beforeEach(() => {
    Vue.options.components = {};
  });

  it('should not render if there are no downloadable files', () => {
    renderComponent({
      files: [],
    });

    expect(screen.queryByText(SAVE_BUTTON_TEXT)).not.toBeInTheDocument();
  });

  it('should not render if there are only renderable exercise files', () => {
    renderComponent({
      files: [getDownloadableFile(true)],
    });

    expect(screen.queryByText(SAVE_BUTTON_TEXT)).not.toBeInTheDocument();
  });

  it('should render if there are renderable document files', () => {
    renderComponent({
      files: [getDownloadableFile()],
    });

    expect(screen.getByText(SAVE_BUTTON_TEXT)).toBeInTheDocument();
  });
});

describe('DownloadButton files', () => {
  // A video's file that isn't on the device, as when the video plays from YouTube
  const fileNotOnDevice = {
    preset: 'high_res_video',
    available: false,
    file_size: 100,
    storage_url: null,
    extension: 'mp4',
    checksum: '1234567890',
  };

  it("does not render for a file that isn't on the device", () => {
    kolibri.presetViewerComponent = jest.fn(() => ({ template: '<div></div>' }));
    renderComponent({ files: [fileNotOnDevice] });

    expect(screen.queryByText(SAVE_BUTTON_TEXT)).not.toBeInTheDocument();
  });

  it("takes files that aren't on the device, and so have no URL", () => {
    expect(DownloadButton.props.files.validator([fileNotOnDevice])).toBe(true);
  });

  it('refuses a file without its checksum', () => {
    expect(
      DownloadButton.props.files.validator([{ ...fileNotOnDevice, checksum: undefined }]),
    ).toBe(false);
  });
});
