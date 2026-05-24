import {
  SessionStateKind,
  type FinalizingSessionState,
  type ResultSessionState,
  type SessionScore,
} from "../types.mjs";

export function storeSessionResult(
  session: FinalizingSessionState,
  score: SessionScore | null,
  scoreError: string | null,
): ResultSessionState {
  const { blockUploads, pendingScoreError, ...sessionWithoutUploads } = session;
  void blockUploads;
  void pendingScoreError;

  return {
    ...sessionWithoutUploads,
    result: {
      score,
      scoreError,
    },
    state: SessionStateKind.Results,
  };
}
