import { collectImageUrls } from "../selectors.mjs";
import {
  SessionStateKind,
  type IatDetail,
  type PreloadingSessionState,
  type ReviewSessionState,
  type SessionBootstrap,
} from "../types.mjs";

export function createSessionState(iatDetail: IatDetail, bootstrap: SessionBootstrap): ReviewSessionState {
  return {
    bootstrap,
    iatDetail,
    state: SessionStateKind.Review,
  };
}

export function beginPreloading(session: ReviewSessionState, startedAt = new Date()): PreloadingSessionState {
  return {
    ...session,
    preload: {
      failures: [],
      inFlightCount: 0,
      lastProgressAt: startedAt,
      loaded: 0,
      running: false,
      startedAt,
      total: collectImageUrls(session.bootstrap).length,
    },
    state: SessionStateKind.Preloading,
  };
}
