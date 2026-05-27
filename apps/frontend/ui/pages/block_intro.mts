import { type BlockIntroSessionState, type RuntimeState, type SessionBlock } from "../../state/types.mjs";
import { canAdvanceSession } from "../../state/block_uploads.mjs";
import {
  buildSessionPage,
  buildStageFrame,
  buildStimulusSurface,
  buildStimulusSurfaceOverlay,
  createActionButton,
} from "../parts.mjs";

export function buildBlockIntroPage(
  document: Document,
  runtime: RuntimeState,
  session: BlockIntroSessionState,
  block: SessionBlock,
) {
  const uploadError = session.blockUpload.uploadError;
  const canAdvance = canAdvanceSession(session);
  const showResponseHint = canAdvance || session.starting;
  const title = buildTitle(session, block, canAdvance, uploadError);
  const detail = buildDetail(session, runtime, canAdvance, uploadError);
  const stageStatus = `${block.is_practice ? "Practice block" : "Block"} ${session.currentBlockIndex + 1} of ${session.bootstrap.blocks.length}`;
  const upcomingTrial = session.starting ? (block.trials[0] ?? null) : null;
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

  const stageFrame = buildStageFrame(
    document,
    block,
    "feedback feedback-hint",
    runtime.device.prefersTouchInput,
    stageStatus,
    surface,
    showResponseHint ? "Red X is wrong response." : undefined,
    showResponseHint ? "X" : undefined,
    showResponseHint ? "is wrong response" : undefined,
    !canAdvance,
  );

  if (uploadError !== null) {
    const toolbar = document.createElement("div");
    toolbar.className = "toolbar";
    toolbar.append(
      createActionButton(
        document,
        "retry-uploads",
        "button",
        session.blockUpload.uploading ? "Retrying..." : "Retry saving",
        session.blockUpload.uploading,
      ),
    );
    stageFrame.append(toolbar);
  }

  return buildSessionPage(document, session.iatDetail.title, stageFrame);
}

function buildTitle(
  session: BlockIntroSessionState,
  block: SessionBlock,
  canAdvance: boolean,
  uploadError: string | null,
) {
  if (session.starting) {
    return "Starting block...";
  }

  if (uploadError !== null) {
    return "Responses not saved";
  }
  if (!canAdvance) {
    return "Saving responses...";
  }

  return block.is_practice ? "Practice block" : "Next block";
}

function buildDetail(
  session: BlockIntroSessionState,
  runtime: RuntimeState,
  canAdvance: boolean,
  uploadError: string | null,
) {
  if (session.starting) {
    return "Get ready for the first stimulus.";
  }

  if (uploadError !== null) {
    return "Retry saving your responses before starting the next block.";
  }
  if (!canAdvance) {
    return "The next block will be available when your progress has been saved.";
  }

  return runtime.device.prefersTouchInput ? "Tap a side to begin this block." : "Press E or I to begin this block.";
}

function buildStageMessageSurface(document: Document, title: string, detail: string) {
  const surface = document.createElement("div");
  surface.className = "stimulus-surface";
  surface.append(buildStimulusSurfaceOverlay(document, title, detail));
  return surface;
}
