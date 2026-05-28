import { canAdvanceSession } from "./block_uploads.mjs";
import { currentTrial } from "./selectors.mjs";
import { ResponseSide, SessionStateKind, type RuntimeState } from "./types.mjs";

export type AutomationInputMode = "keyboard" | "touch";

export type AutomationSessionState = "block_intro" | "catalog" | "results" | "review" | "trial";

export interface AutomationSnapshot {
  blockIndex: number | null;
  canAdvance: boolean;
  correctResponseSide: "left" | "right" | null;
  iatSlug: string | null;
  inputMode: AutomationInputMode;
  pending: boolean;
  sessionKey: string | null;
  sessionState: AutomationSessionState;
  trialIndex: number | null;
  trialStartedAtMs: number | null;
}

export function buildAutomationSnapshot(runtime: RuntimeState): AutomationSnapshot {
  const inputMode: AutomationInputMode = runtime.device.prefersTouchInput ? "touch" : "keyboard";
  if (runtime.session === null) {
    return {
      blockIndex: null,
      canAdvance: false,
      correctResponseSide: null,
      iatSlug: null,
      inputMode,
      pending: runtime.catalog.loading,
      sessionKey: null,
      sessionState: "catalog",
      trialIndex: null,
      trialStartedAtMs: null,
    };
  }

  const snapshot: AutomationSnapshot = {
    blockIndex: null,
    canAdvance: false,
    correctResponseSide: null,
    iatSlug: runtime.session.iatDetail.slug,
    inputMode,
    pending: false,
    sessionKey: runtime.session.bootstrap.session_key,
    sessionState: mapSessionState(runtime.session.state),
    trialIndex: null,
    trialStartedAtMs: null,
  };

  switch (runtime.session.state) {
    case SessionStateKind.Review:
      return {
        ...snapshot,
        canAdvance: canAdvanceSession(runtime.session),
      };

    case SessionStateKind.Results:
      return {
        ...snapshot,
        pending: runtime.session.pending,
      };

    case SessionStateKind.BlockIntro:
      return {
        ...snapshot,
        blockIndex: runtime.session.currentBlockIndex,
        canAdvance: canAdvanceSession(runtime.session),
      };

    case SessionStateKind.Trial: {
      const trial = currentTrial(runtime.session);
      if (trial === null) {
        throw new Error("Expected one active trial when building one trial automation snapshot.");
      }

      return {
        ...snapshot,
        blockIndex: runtime.session.currentBlockIndex,
        correctResponseSide: trial.correct_response_side === ResponseSide.Left ? "left" : "right",
        trialIndex: runtime.session.currentTrialIndex,
        trialStartedAtMs: runtime.session.trial.startedAtMs,
      };
    }
  }
}

function mapSessionState(sessionState: SessionStateKind) {
  switch (sessionState) {
    case SessionStateKind.BlockIntro:
      return "block_intro";

    case SessionStateKind.Results:
      return "results";

    case SessionStateKind.Review:
      return "review";

    case SessionStateKind.Trial:
      return "trial";
  }
}
