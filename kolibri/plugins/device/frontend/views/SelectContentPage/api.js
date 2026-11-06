import TaskResource from 'kolibri/apiResources/TaskResource';
import { TaskTypes } from 'kolibri-common/utils/syncTaskUtils';

export function startImportTask(params) {
  const { importSource, channelId, channelName, included, excluded, stream } = params;

  const taskParams = {
    channel_id: channelId,
    channel_name: channelName,
    node_ids: included,
    exclude_node_ids: excluded,
  };

  // Leave out the files of videos, to play them from YouTube
  if (stream) {
    taskParams.stream = true;
  }

  if (importSource.type === 'peer' || importSource.type === 'studio') {
    if (importSource.id) {
      taskParams.peer = importSource.id;
    }
    taskParams.type = TaskTypes.REMOTECONTENTIMPORT;
  } else if (importSource.type === 'drive') {
    taskParams.drive_id = importSource.driveId;
    taskParams.type = TaskTypes.DISKCONTENTIMPORT;
  } else {
    return Promise.reject();
  }
  return TaskResource.startTask(taskParams);
}
