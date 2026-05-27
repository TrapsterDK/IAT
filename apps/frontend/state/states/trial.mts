import { currentBlock, currentTrial } from "../selectors.mjs";
import {
  ResponseSide,
  SessionStateKind,
  TrialAdvanceKind,
  TrialResponseKind,
  type BlockIntroSessionState,
  type CompletedTrial,
  type PendingResultSessionState,
  type TrialEvent,
  type TrialSessionState,
} from "../types.mjs";

type TrialResponseResult =
  | {
      kind: TrialResponseKind.Accepted;
      completedTrial: CompletedTrial;
    }
  | {
      kind: TrialResponseKind.Ignored | TrialResponseKind.Incorrect;
    };

type TrialAdvanceResult =
  | {
      kind: TrialAdvanceKind.AdvancedBlock;
      session: BlockIntroSessionState;
    }
  | {
      kind: TrialAdvanceKind.AdvancedTrial;
      session: TrialSessionState;
    }
  | {
      kind: TrialAdvanceKind.AdvancedResult;
      session: PendingResultSessionState;
    }
  | {
      kind: TrialAdvanceKind.Ignored;
      session: TrialSessionState;
    };

export function registerTrialResponse(
  session: TrialSessionState,
  side: ResponseSide,
  elapsedMs: number,
): TrialResponseResult {
  const trial = currentTrial(session);
  if (trial === null || session.trial.startedAtMs === null || session.trial.responseLocked) {
    return { kind: TrialResponseKind.Ignored };
  }

  const updatedEvents: TrialEvent[] = [...session.trial.activeEvents, { elapsedMs, eventType: side }];

  if (side !== trial.correct_response_side) {
    session.trial.activeEvents = updatedEvents;
    return { kind: TrialResponseKind.Incorrect };
  }

  session.trial.responseLocked = true;
  session.trial.activeEvents = [];
  return {
    completedTrial: { events: updatedEvents },
    kind: TrialResponseKind.Accepted,
  };
}

export function advanceSessionAfterCompletedTrial(
  session: TrialSessionState,
  completedTrial: CompletedTrial,
): TrialAdvanceResult {
  const block = currentBlock(session);
  if (block === null) {
    return { kind: TrialAdvanceKind.Ignored, session };
  }

  const updatedBlockTrials = [...session.currentBlockTrials, completedTrial];
  const isLastTrial = session.currentTrialIndex >= block.trials.length - 1;
  if (!isLastTrial) {
    return {
      kind: TrialAdvanceKind.AdvancedTrial,
      session: {
        ...session,
        currentBlockTrials: updatedBlockTrials,
        currentTrialIndex: session.currentTrialIndex + 1,
        trial: {
          activeEvents: [],
          responseLocked: false,
          startedAtMs: null,
        },
      },
    };
  }

  const nextBlockUpload = {
    blockIndex: session.currentBlockIndex + 1,
    payload: {
      trials: updatedBlockTrials,
    },
  };
  const nextBlockIndex = session.currentBlockIndex + 1;
  const { currentBlockIndex, currentBlockTrials, currentTrialIndex, trial, ...sessionWithoutTrialProgress } = session;
  void currentBlockIndex;
  void currentBlockTrials;
  void currentTrialIndex;
  void trial;
  const hasMoreBlocks = session.currentBlockIndex < session.bootstrap.blocks.length - 1;
  if (hasMoreBlocks) {
    return {
      kind: TrialAdvanceKind.AdvancedBlock,
      session: {
        ...sessionWithoutTrialProgress,
        blockUpload: {
          pendingUpload: nextBlockUpload,
          uploadError: null,
          uploading: false,
        },
        currentBlockIndex: nextBlockIndex,
        starting: false,
        state: SessionStateKind.BlockIntro,
      },
    };
  }

  return {
    kind: TrialAdvanceKind.AdvancedResult,
    session: {
      ...sessionWithoutTrialProgress,
      blockUpload: {
        pendingUpload: nextBlockUpload,
        uploadError: null,
        uploading: false,
      },
      pending: true,
      result: {
        score: null,
        scoreError: null,
      },
      state: SessionStateKind.Results,
    },
  };
}
