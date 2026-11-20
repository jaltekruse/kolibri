import { fireEvent, render, screen } from '@testing-library/vue';
import { Store } from 'vuex';
import { useDevicesWithFilter } from 'kolibri-common/components/syncComponentSet/SelectDeviceModalGroup/useDevices';
import { LearningActivities } from 'kolibri/constants';
import { coreStrings } from 'kolibri/uiText/commonCoreStrings';
import { quickAssignStrings } from 'kolibri-common/strings/quickAssignStrings';
import LearningActivityBar from '../LearningActivityBar';

jest.mock('kolibri-common/components/syncComponentSet/SelectDeviceModalGroup/useDevices');

const { quickAssignAction$ } = quickAssignStrings;
const { viewInformation$ } = coreStrings;

function renderBar(props = {}) {
  const store = new Store({
    state: { core: { loading: false } },
    mutations: { SET_SHOW_COMPLETE_CONTENT_MODAL: jest.fn() },
  });
  return render(LearningActivityBar, {
    props: {
      resourceTitle: 'Two-step equations',
      learningActivities: [LearningActivities.PRACTICE],
      ...props,
    },
    store,
  });
}

describe('LearningActivityBar quick assign', () => {
  beforeEach(() => {
    useDevicesWithFilter.mockReturnValue({ devices: [] });
  });

  it('offers to quick assign the resource', async () => {
    const { emitted } = renderBar({ showQuickAssign: true });

    await fireEvent.click(await screen.findByRole('button', { name: quickAssignAction$() }));

    expect(emitted().quickAssign).toHaveLength(1);
  });

  it('does not offer it unless asked to', async () => {
    renderBar();

    // The bar has laid out its actions
    await screen.findByRole('button', { name: viewInformation$() });
    expect(screen.queryByRole('button', { name: quickAssignAction$() })).not.toBeInTheDocument();
  });
});
