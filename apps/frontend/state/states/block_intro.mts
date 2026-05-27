import { SessionStateKind, type BlockIntroSessionState, type TrialSessionState } from "../types.mjs";

export function beginStartingBlock(session: BlockIntroSessionState): BlockIntroSessionState {
  return {
    ...session,
    starting: true,
  };
}

export function beginTrial(session: BlockIntroSessionState): TrialSessionState {
  const { blockUpload, starting, ...sessionWithoutBlockIntro } = session;
  void blockUpload;
  void starting;

  return {
    ...sessionWithoutBlockIntro,
    currentBlockTrials: [],
    currentTrialIndex: 0,
    state: SessionStateKind.Trial,
    trial: {
      activeEvents: [],
      responseLocked: false,
      startedAtMs: null,
    },
  };
}
