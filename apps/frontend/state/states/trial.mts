import { currentBlock, currentTrial } from "../selectors.mjs";
import {
  ResponseSide,
  SessionStateKind,
  TrialAdvanceKind,
  TrialResponseKind,
  type BlockIntroSessionState,
  type CompletedTrial,
  type FinalizingSessionState,
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
      kind: TrialAdvanceKind.Finalizing;
      session: FinalizingSessionState;
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
  if (trial === null || session.trial.responseLocked) {
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
  nextTrialStartedAtMs: number,
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
          startedAtMs: nextTrialStartedAtMs,
        },
      },
    };
  }

  const nextBlockUploads = {
    ...session.blockUploads,
    queuedBlockUploads: [
      ...session.blockUploads.queuedBlockUploads,
      {
        blockIndex: session.currentBlockIndex + 1,
        lastError: null,
        payload: {
          trials: updatedBlockTrials,
        },
        uploaded: false,
      },
    ],
  };
  const { trial, ...sessionWithoutTrial } = session;
  void trial;
  const hasMoreBlocks = session.currentBlockIndex < session.bootstrap.blocks.length - 1;
  if (hasMoreBlocks) {
    return {
      kind: TrialAdvanceKind.AdvancedBlock,
      session: {
        ...sessionWithoutTrial,
        blockUploads: nextBlockUploads,
        currentBlockIndex: session.currentBlockIndex + 1,
        state: SessionStateKind.BlockIntro,
      },
    };
  }

  return {
    kind: TrialAdvanceKind.Finalizing,
    session: {
      ...sessionWithoutTrial,
      blockUploads: nextBlockUploads,
      pendingScoreError: null,
      state: SessionStateKind.Finalizing,
    },
  };
}
