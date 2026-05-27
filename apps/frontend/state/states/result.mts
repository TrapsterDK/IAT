import {
  SessionStateKind,
  type PendingResultSessionState,
  type ResultSessionState,
  type SessionScore,
} from "../types.mjs";

export function storeSessionResult(
  session: PendingResultSessionState,
  score: SessionScore | null,
  scoreError: string | null,
): ResultSessionState {
  const { blockUpload, pending, ...sessionWithoutPendingResult } = session;
  void blockUpload;
  void pending;

  return {
    ...sessionWithoutPendingResult,
    pending: false,
    result: {
      score,
      scoreError,
    },
    state: SessionStateKind.Results,
  };
}
