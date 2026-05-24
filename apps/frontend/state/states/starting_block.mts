import { SessionStateKind, type StartingBlockSessionState, type TrialSessionState } from "../types.mjs";

export function beginTrial(session: StartingBlockSessionState, startedAtMs: number): TrialSessionState {
  return {
    ...session,
    currentBlockTrials: [],
    currentTrialIndex: 0,
    state: SessionStateKind.Trial,
    trial: {
      activeEvents: [],
      responseLocked: false,
      startedAtMs,
    },
  };
}
