import { currentTrial } from "./selectors.mjs";
import { ResponseSide, SessionStateKind, type RuntimeState } from "./types.mjs";

export type AutomationInputMode = "keyboard" | "touch";

export type AutomationSessionState =
  | "block_intro"
  | "catalog"
  | "finalizing"
  | "preloading"
  | "results"
  | "review"
  | "starting_block"
  | "trial";

export interface AutomationSnapshot {
  blockIndex: number | null;
  correctResponseSide: "left" | "right" | null;
  iatSlug: string | null;
  inputMode: AutomationInputMode;
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
      correctResponseSide: null,
      iatSlug: null,
      inputMode,
      sessionKey: null,
      sessionState: "catalog",
      trialIndex: null,
      trialStartedAtMs: null,
    };
  }

  const snapshot: AutomationSnapshot = {
    blockIndex: null,
    correctResponseSide: null,
    iatSlug: runtime.session.iatDetail.slug,
    inputMode,
    sessionKey: runtime.session.bootstrap.session_key,
    sessionState: mapSessionState(runtime.session.state),
    trialIndex: null,
    trialStartedAtMs: null,
  };

  switch (runtime.session.state) {
    case SessionStateKind.Review:
    case SessionStateKind.Preloading:
    case SessionStateKind.Finalizing:
    case SessionStateKind.Results:
      return snapshot;

    case SessionStateKind.BlockIntro:
    case SessionStateKind.StartingBlock:
      return {
        ...snapshot,
        blockIndex: runtime.session.currentBlockIndex,
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

    case SessionStateKind.Finalizing:
      return "finalizing";

    case SessionStateKind.Preloading:
      return "preloading";

    case SessionStateKind.Results:
      return "results";

    case SessionStateKind.Review:
      return "review";

    case SessionStateKind.StartingBlock:
      return "starting_block";

    case SessionStateKind.Trial:
      return "trial";
  }
}
