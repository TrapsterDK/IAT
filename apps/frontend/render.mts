import { publishAutomationSnapshot } from "./automation.mjs";
import { currentBlock, currentTrial } from "./state/selectors.mjs";
import { SessionStateKind, type RuntimeState } from "./state/types.mjs";
import { createElement } from "./ui/dom.mjs";
import { buildBlockIntroPage } from "./ui/pages/block_intro.mjs";
import { buildCatalogPage } from "./ui/pages/catalog.mjs";
import { buildResultPage } from "./ui/pages/result.mjs";
import { buildReviewPage } from "./ui/pages/review.mjs";
import { buildTrialPage } from "./ui/pages/trial.mjs";
import { buildErrorBanner } from "./ui/parts.mjs";

export function render(appRoot: HTMLElement, runtime: RuntimeState) {
  const document = appRoot.ownerDocument;
  const shell = createElement(document, "div", "app-shell");
  const errorBanner = buildErrorBanner(document, runtime.ui.screenError);

  const nextSessionState = runtime.session?.state ?? null;
  if (shouldScrollToTop(lastRenderedSessionState, nextSessionState)) {
    window.scrollTo?.({ top: 0 });
  }
  lastRenderedSessionState = nextSessionState;

  if (errorBanner !== null) {
    shell.append(errorBanner);
  }

  shell.append(buildPage(document, runtime));
  appRoot.replaceChildren(shell);

  publishAutomationSnapshot(window, runtime);
}

let lastRenderedSessionState: SessionStateKind | null = null;

function buildPage(document: Document, runtime: RuntimeState) {
  const session = runtime.session;
  if (session === null) {
    return buildCatalogPage(document, runtime);
  }

  switch (session.state) {
    case SessionStateKind.Results:
      return buildResultPage(document, session);

    case SessionStateKind.Review:
      return buildReviewPage(document, runtime, session);

    case SessionStateKind.BlockIntro: {
      const block = currentBlock(session);
      if (block === null) {
        throw new Error("Expected a current block for the block intro screen.");
      }

      return buildBlockIntroPage(document, runtime, session, block);
    }

    case SessionStateKind.Trial: {
      const block = currentBlock(session);
      const trial = currentTrial(session);
      if (block === null || trial === null) {
        throw new Error("Expected an active trial for the trial screen.");
      }

      return buildTrialPage(document, runtime, session, block, trial);
    }
  }
}

function shouldScrollToTop(previousSessionState: SessionStateKind | null, nextSessionState: SessionStateKind | null) {
  if (previousSessionState === nextSessionState) {
    return false;
  }

  return !(isStageSessionState(previousSessionState) && isStageSessionState(nextSessionState));
}

function isStageSessionState(sessionState: SessionStateKind | null) {
  return sessionState === SessionStateKind.BlockIntro || sessionState === SessionStateKind.Trial;
}
