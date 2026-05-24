import { PRELOAD_STALLED_AFTER_MS } from "../../core/config.mjs";
import { formatDuration } from "../../core/utils.mjs";
import type { PreloadingSessionState } from "../../state/types.mjs";
import { buildProgressBar, buildSessionPage, createActionButton } from "../parts.mjs";

export function buildPreloadingPage(document: Document, session: PreloadingSessionState) {
  const section = document.createElement("section");
  section.className = "stack";
  const totalCount = session.preload.total;
  const progressFraction = totalCount === 0 ? 1 : session.preload.loaded / totalCount;
  const progressValueText =
    totalCount === 0 ? "No images to preload." : `${session.preload.loaded} of ${totalCount} images loaded.`;
  const lastProgressAgeMs = Math.max(0, Date.now() - session.preload.lastProgressAt.getTime());

  let message = "Preparing the test.";
  if (session.preload.failures.length > 0 && !session.preload.running) {
    message = "Some images did not load. Try again to continue.";
  } else if (
    session.preload.running &&
    session.preload.inFlightCount > 0 &&
    lastProgressAgeMs >= PRELOAD_STALLED_AFTER_MS
  ) {
    message = `Still loading. Last progress was ${formatDuration(lastProgressAgeMs)} ago.`;
  }

  const heading = document.createElement("h2");
  heading.className = "section-title";
  heading.textContent = "Preparing the test";

  const messageElement = document.createElement("p");
  messageElement.className = "muted";
  messageElement.textContent = message;

  section.append(
    heading,
    messageElement,
    buildProgressBar(document, progressFraction, "Image preload progress", progressValueText),
  );

  if (session.preload.failures.length > 0) {
    const toolbar = document.createElement("div");
    toolbar.className = "toolbar";
    toolbar.append(
      createActionButton(
        document,
        "retry-preload",
        "button",
        session.preload.running ? "Loading..." : "Retry",
        session.preload.running,
      ),
    );
    section.append(toolbar);
  }

  return buildSessionPage(document, session.iatDetail.title, section);
}
