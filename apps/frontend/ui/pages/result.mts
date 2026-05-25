import type { ResultSessionState, RuntimeState } from "../../state/types.mjs";
import { applyAutomationMetadata, createActionButton } from "../parts.mjs";

export function buildResultPage(document: Document, runtime: RuntimeState, session: ResultSessionState) {
  const page = document.createElement("section");
  page.className = "page page-centered";

  const panel = document.createElement("section");
  panel.className = "stack panel-centered";

  const title = document.createElement("h1");
  title.className = "page-title";
  title.textContent = session.iatDetail.title;

  const headline = document.createElement("p");
  headline.className = "result-headline";
  headline.textContent = session.result.scoreError ?? session.result.score?.headline ?? "Result ready.";

  const score = document.createElement("p");
  score.className = "result-score";
  score.textContent = session.result.score === null ? "" : session.result.score.d_score.toFixed(3);

  panel.append(title, headline, score);

  const toolbar = document.createElement("div");
  toolbar.className = "toolbar toolbar-center";
  toolbar.append(createActionButton(document, "back-to-catalog", "button button-primary", "Back to catalog"));

  page.append(panel, toolbar);
  return applyAutomationMetadata(
    page,
    runtime.device.prefersTouchInput ? "touch" : "keyboard",
    "results",
    session.bootstrap.session_key,
    session.iatDetail.slug,
  );
}
