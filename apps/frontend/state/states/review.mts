import { collectImageUrls } from "../selectors.mjs";
import {
  SessionStateKind,
  type BlockIntroSessionState,
  type IatDetail,
  type ReviewSessionState,
  type SessionBootstrap,
} from "../types.mjs";

export interface PreloadProgressSnapshot {
  failures: string[];
  inFlightCount: number;
  lastProgressAt: Date;
  loaded: number;
  startedAt: Date;
  total: number;
}

export function createSessionState(
  iatDetail: IatDetail,
  bootstrap: SessionBootstrap,
  startedAt = new Date(),
): ReviewSessionState {
  return {
    bootstrap,
    iatDetail,
    preload: {
      failures: [],
      inFlightCount: 0,
      lastProgressAt: startedAt,
      loaded: 0,
      running: false,
      startedAt,
      total: collectImageUrls(bootstrap).length,
    },
    state: SessionStateKind.Review,
  };
}

export function applyPreloadProgress(session: ReviewSessionState, preloadProgress: PreloadProgressSnapshot) {
  session.preload.total = preloadProgress.total;
  session.preload.loaded = preloadProgress.loaded;
  session.preload.inFlightCount = preloadProgress.inFlightCount;
  session.preload.failures = [...preloadProgress.failures];
  session.preload.startedAt = preloadProgress.startedAt;
  session.preload.lastProgressAt = preloadProgress.lastProgressAt;
}

export function setPreloadRunning(session: ReviewSessionState, preloadRunning: boolean) {
  session.preload.running = preloadRunning;
}

export function beginBlockIntro(session: ReviewSessionState): BlockIntroSessionState {
  const { preload, ...sessionWithoutPreload } = session;
  void preload;

  return {
    ...sessionWithoutPreload,
    blockUpload: {
      pendingUpload: null,
      uploadError: null,
      uploading: false,
    },
    currentBlockIndex: 0,
    starting: false,
    state: SessionStateKind.BlockIntro,
  };
}
