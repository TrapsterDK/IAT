import { SessionStateKind, type BlockIntroSessionState, type PreloadingSessionState } from "../types.mjs";

export interface PreloadProgressSnapshot {
  failures: string[];
  inFlightCount: number;
  lastProgressAt: Date;
  loaded: number;
  startedAt: Date;
  total: number;
}

export function applyPreloadProgress(session: PreloadingSessionState, preloadProgress: PreloadProgressSnapshot) {
  session.preload.total = preloadProgress.total;
  session.preload.loaded = preloadProgress.loaded;
  session.preload.inFlightCount = preloadProgress.inFlightCount;
  session.preload.failures = [...preloadProgress.failures];
  session.preload.startedAt = preloadProgress.startedAt;
  session.preload.lastProgressAt = preloadProgress.lastProgressAt;
}

export function setPreloadRunning(session: PreloadingSessionState, preloadRunning: boolean) {
  session.preload.running = preloadRunning;
}

export function beginBlockIntro(session: PreloadingSessionState): BlockIntroSessionState {
  const { preload, ...sessionWithoutPreload } = session;
  void preload;
  return {
    blockUploads: {
      queuedBlockUploads: [],
      uploading: false,
    },
    ...sessionWithoutPreload,
    currentBlockIndex: 0,
    state: SessionStateKind.BlockIntro,
  };
}
