import { type RuntimeState, type SessionBlock, type SessionTrial, type TrialSessionState } from "../../state/types.mjs";
import { buildSessionPage, buildStageFrame, buildStimulusSurface } from "../parts.mjs";

export function buildTrialPage(
  document: Document,
  runtime: RuntimeState,
  session: TrialSessionState,
  block: SessionBlock,
  trial: SessionTrial,
) {
  const lastEvent = session.trial.activeEvents.at(-1);
  const showIncorrectFeedback = lastEvent !== undefined && lastEvent.eventType !== trial.correct_response_side;

  return buildSessionPage(
    document,
    session.iatDetail.title,
    buildStageFrame(
      document,
      block,
      showIncorrectFeedback ? "feedback feedback-error" : "feedback",
      runtime.device.prefersTouchInput,
      `Trial ${session.currentTrialIndex + 1} of ${block.trials.length}`,
      buildStimulusSurface(document, runtime, trial.stimulus),
      showIncorrectFeedback
        ? runtime.device.prefersTouchInput
          ? "Incorrect. Tap the other side to continue."
          : "Incorrect. Press the other side to continue."
        : undefined,
      showIncorrectFeedback ? "X" : undefined,
    ),
  );
}
