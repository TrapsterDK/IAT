import {
  type BlockIntroSessionState,
  SessionStateKind,
  type FinalizingSessionState,
  type QueuedBlockUpload,
  type SessionState,
  type StartingBlockSessionState,
  type TrialSessionState,
} from "./types.mjs";

export function hasBlockUploads(
  session: SessionState,
): session is BlockIntroSessionState | StartingBlockSessionState | TrialSessionState | FinalizingSessionState {
  switch (session.state) {
    case SessionStateKind.BlockIntro:
    case SessionStateKind.StartingBlock:
    case SessionStateKind.Trial:
    case SessionStateKind.Finalizing:
      return true;

    default:
      return false;
  }
}

export function nextPendingBlockUpload(
  session: BlockIntroSessionState | StartingBlockSessionState | TrialSessionState | FinalizingSessionState,
): QueuedBlockUpload | null {
  return session.blockUploads.queuedBlockUploads.find((queuedUpload) => !queuedUpload.uploaded) ?? null;
}

export function hasPendingBlockUploads(
  session: BlockIntroSessionState | StartingBlockSessionState | TrialSessionState | FinalizingSessionState,
): boolean {
  return nextPendingBlockUpload(session) !== null;
}

export function setBlockUploadsActive(
  session: BlockIntroSessionState | StartingBlockSessionState | TrialSessionState | FinalizingSessionState,
  uploading: boolean,
) {
  session.blockUploads.uploading = uploading;
}

export function markBlockUploadStarted(queuedUpload: QueuedBlockUpload) {
  queuedUpload.lastError = null;
}

export function markBlockUploadFailed(queuedUpload: QueuedBlockUpload, message: string) {
  queuedUpload.lastError = message;
}

export function markBlockUploadUploaded(queuedUpload: QueuedBlockUpload) {
  queuedUpload.uploaded = true;
  queuedUpload.lastError = null;
}
