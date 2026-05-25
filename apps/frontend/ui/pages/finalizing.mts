import type { FinalizingSessionState, RuntimeState } from "../../state/types.mjs";
import { applyAutomationMetadata, buildMessage, createActionButton } from "../parts.mjs";

export function buildFinalizingPage(document: Document, runtime: RuntimeState, session: FinalizingSessionState) {
  const page = document.createElement("section");
  page.className = "page page-centered";

  const section = document.createElement("section");
  section.className = "stack stack-sm panel-centered";
  const uploadError =
    session.blockUploads.queuedBlockUploads.find((queuedUpload) => queuedUpload.lastError !== null)?.lastError ?? null;
  const hasPendingUploads = session.blockUploads.queuedBlockUploads.some((queuedUpload) => !queuedUpload.uploaded);

  let message = "Preparing your result.";
  if (session.pendingScoreError !== null) {
    message = session.pendingScoreError;
  } else if (session.blockUploads.uploading && hasPendingUploads) {
    message = "Saving your responses.";
  }

  const heading = document.createElement("h2");
  heading.className = "section-title";
  heading.textContent = "Calculating...";

  const messageElement = document.createElement("p");
  messageElement.className = "muted";
  messageElement.textContent = message;

  section.append(heading, messageElement);

  if (uploadError !== null) {
    section.append(buildMessage(document, uploadError));
  }

  if (uploadError !== null || session.pendingScoreError !== null) {
    const toolbar = document.createElement("div");
    toolbar.className = "toolbar";
    toolbar.append(
      createActionButton(
        document,
        "retry-uploads",
        "button",
        session.blockUploads.uploading ? "Retrying..." : "Retry",
        session.blockUploads.uploading,
      ),
    );
    section.append(toolbar);
  }

  page.append(section);
  return applyAutomationMetadata(
    page,
    runtime.device.prefersTouchInput ? "touch" : "keyboard",
    "finalizing",
    session.bootstrap.session_key,
    session.iatDetail.slug,
  );
}
