import type { ResultSessionState } from "../../state/types.mjs";
import { buildMessage, createActionButton } from "../parts.mjs";

export function buildResultPage(document: Document, session: ResultSessionState) {
  const page = document.createElement("section");
  page.className = "page page-centered";

  const panel = document.createElement("section");
  panel.className = "stack panel-centered";

  const title = document.createElement("h1");
  title.className = "page-title";
  title.textContent = session.pending ? "Calculating..." : session.iatDetail.title;

  const headline = document.createElement("p");
  headline.className = "result-headline";
  headline.textContent = buildHeadline(session);

  const score = document.createElement("p");
  score.className = "result-score";
  score.textContent = session.pending || session.result.score === null ? "" : session.result.score.d_score.toFixed(3);

  panel.append(title, headline, score);

  if (session.pending && session.blockUpload.uploadError !== null) {
    panel.append(buildMessage(document, session.blockUpload.uploadError));
  }

  const toolbar = document.createElement("div");
  toolbar.className = "toolbar toolbar-center";

  if (session.pending && canRetryPendingResult(session)) {
    toolbar.append(
      createActionButton(
        document,
        "retry-uploads",
        "button",
        session.blockUpload.uploading ? "Retrying..." : "Retry",
        session.blockUpload.uploading,
      ),
    );
  }

  toolbar.append(createActionButton(document, "back-to-catalog", "button button-primary", "Back to catalog"));

  page.append(panel, toolbar);
  return page;
}

function buildHeadline(session: ResultSessionState) {
  if (!session.pending) {
    return session.result.scoreError ?? session.result.score?.headline ?? "Result ready.";
  }

  if (session.result.scoreError !== null) {
    return session.result.scoreError;
  }

  if (session.blockUpload.uploadError !== null) {
    return "Retry saving your responses.";
  }

  if (session.blockUpload.uploading && session.blockUpload.pendingUpload !== null) {
    return "Saving your responses.";
  }

  return "Preparing your result.";
}

function canRetryPendingResult(session: Extract<ResultSessionState, { pending: true }>) {
  return session.blockUpload.uploadError !== null || session.result.scoreError !== null;
}
