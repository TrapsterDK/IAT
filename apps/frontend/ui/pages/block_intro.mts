import {
  SessionStateKind,
  type BlockIntroSessionState,
  type RuntimeState,
  type SessionBlock,
  type StartingBlockSessionState,
} from "../../state/types.mjs";
import {
  applyAutomationMetadata,
  buildSessionPage,
  buildStageFrame,
  buildStimulusSurface,
  buildStimulusSurfaceOverlay,
} from "../parts.mjs";

export function buildBlockIntroPage(
  document: Document,
  runtime: RuntimeState,
  session: BlockIntroSessionState | StartingBlockSessionState,
  block: SessionBlock,
) {
  const upcomingTrial = session.state === SessionStateKind.StartingBlock ? (block.trials[0] ?? null) : null;
  const title =
    session.state === SessionStateKind.StartingBlock
      ? "Starting block..."
      : block.is_practice
        ? "Practice block"
        : "Next block";
  const detail =
    session.state === SessionStateKind.StartingBlock
      ? "Get ready for the first stimulus."
      : runtime.device.prefersTouchInput
        ? "Tap a side to begin this block."
        : "Press E or I to begin this block.";
  const stageStatus = `${block.is_practice ? "Practice block" : "Block"} ${session.currentBlockIndex + 1} of ${session.bootstrap.blocks.length}`;
  const surface =
    upcomingTrial === null
      ? buildStageMessageSurface(document, title, detail)
      : buildStimulusSurface(
          document,
          runtime,
          upcomingTrial.stimulus,
          true,
          buildStimulusSurfaceOverlay(document, title, detail),
        );

  return applyAutomationMetadata(
    buildSessionPage(
      document,
      session.iatDetail.title,
      buildStageFrame(
        document,
        block,
        "feedback feedback-hint",
        runtime.device.prefersTouchInput,
        stageStatus,
        surface,
        "Red X is wrong response.",
        "X",
        "is wrong response",
      ),
    ),
    runtime.device.prefersTouchInput ? "touch" : "keyboard",
    "block_intro",
    session.bootstrap.session_key,
    session.iatDetail.slug,
    session.currentBlockIndex,
  );
}

function buildStageMessageSurface(document: Document, title: string, detail: string) {
  const surface = document.createElement("div");
  surface.className = "stimulus-surface";
  surface.append(buildStimulusSurfaceOverlay(document, title, detail));
  return surface;
}
