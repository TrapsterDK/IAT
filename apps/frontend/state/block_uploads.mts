import {
  type BlockIntroSessionState,
  type PendingBlockUpload,
  type PendingResultSessionState,
  SessionStateKind,
  type ReviewSessionState,
  type SessionState,
} from "./types.mjs";

export function hasBlockUploads(session: SessionState): session is BlockIntroSessionState | PendingResultSessionState {
  switch (session.state) {
    case SessionStateKind.BlockIntro:
      return true;

    case SessionStateKind.Results:
      return session.pending;

    default:
      return false;
  }
}

export function nextPendingBlockUpload(
  session: BlockIntroSessionState | PendingResultSessionState,
): PendingBlockUpload | null {
  return session.blockUpload.pendingUpload;
}

export function hasPendingBlockUploads(session: BlockIntroSessionState | PendingResultSessionState): boolean {
  return nextPendingBlockUpload(session) !== null;
}

export function canAdvanceSession(session: ReviewSessionState | BlockIntroSessionState): boolean {
  if (session.state === SessionStateKind.Review) {
    return (
      !session.preload.running &&
      session.preload.inFlightCount === 0 &&
      session.preload.failures.length === 0 &&
      session.preload.loaded >= session.preload.total
    );
  }

  return !session.starting && !session.blockUpload.uploading && !hasPendingBlockUploads(session);
}

export function setBlockUploadsActive(session: BlockIntroSessionState | PendingResultSessionState, uploading: boolean) {
  session.blockUpload.uploading = uploading;
}

export function markBlockUploadStarted(session: BlockIntroSessionState | PendingResultSessionState) {
  session.blockUpload.uploadError = null;
}

export function markBlockUploadFailed(session: BlockIntroSessionState | PendingResultSessionState, message: string) {
  session.blockUpload.uploadError = message;
}

export function markBlockUploadUploaded(session: BlockIntroSessionState | PendingResultSessionState) {
  session.blockUpload.pendingUpload = null;
  session.blockUpload.uploadError = null;
}
