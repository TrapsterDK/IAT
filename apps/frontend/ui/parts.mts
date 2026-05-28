import type { IatStimulus, RuntimeState } from "../state/types.mjs";
export { createActionButton } from "./dom.mjs";

import { createActionButton, createElement } from "./dom.mjs";

type ResponseLabels = {
  left_labels: readonly string[];
  right_labels: readonly string[];
};

export function buildPageHeader(document: Document, title: string, actions?: HTMLElement) {
  const header = createElement(document, "header", "page-header");
  header.append(createElement(document, "h1", "page-title", title));

  if (actions !== undefined) {
    header.append(actions);
  }

  return header;
}

export function buildMessage(document: Document, message: string) {
  return createElement(document, "p", "message", message);
}

export function buildErrorBanner(document: Document, errorText: string | null) {
  if (errorText === null) {
    return null;
  }

  const banner = createElement(document, "section", "error-banner stack");
  banner.setAttribute("role", "alert");

  const message = createElement(document, "p", undefined, errorText);
  banner.append(message);

  const actions = createElement(document, "div", "toolbar");
  actions.append(createActionButton(document, "clear-error", "button", "Dismiss"));
  banner.append(actions);
  return banner;
}

export function buildProgressBar(
  document: Document,
  progressFraction: number,
  accessibleName: string,
  accessibleValueText?: string,
) {
  const boundedProgress = Math.max(0, Math.min(1, progressFraction));
  const percentage = Math.round(boundedProgress * 100);
  const bar = createElement(document, "div", "progress-bar");
  bar.setAttribute("role", "progressbar");
  bar.setAttribute("aria-label", accessibleName);
  bar.setAttribute("aria-valuemin", "0");
  bar.setAttribute("aria-valuemax", "100");
  bar.setAttribute("aria-valuenow", `${percentage}`);

  if (accessibleValueText !== undefined) {
    bar.setAttribute("aria-valuetext", accessibleValueText);
  }

  const fill = createElement(document, "span", "progress-fill");
  fill.style.width = `${boundedProgress * 100}%`;
  bar.append(fill);
  return bar;
}

export function buildSessionPage(document: Document, title: string, content: HTMLElement) {
  const page = createElement(document, "section", "page");

  const toolbar = createElement(document, "div", "toolbar toolbar-end");
  toolbar.append(createActionButton(document, "back-to-catalog", "button", "Back to catalog"));

  page.append(buildPageHeader(document, title, toolbar), content);
  return page;
}

export function buildStimulusSurface(
  document: Document,
  runtime: RuntimeState,
  stimulus: IatStimulus,
  concealed = false,
  overlay?: HTMLElement,
) {
  const surface = createElement(document, "div", "stimulus-surface");

  if (stimulus.image_url !== null) {
    const preloadedImageUrl = runtime.assets.imageObjectUrls.get(stimulus.image_url);
    if (preloadedImageUrl === undefined) {
      throw new Error(`Expected one preloaded image object URL for '${stimulus.image_url}'.`);
    }

    const image = createElement(
      document,
      "img",
      concealed ? "stimulus-image stimulus-image-concealed" : "stimulus-image",
    );
    image.alt = "Stimulus";
    image.src = preloadedImageUrl;
    surface.append(image);
  } else {
    const text = createElement(
      document,
      "div",
      concealed ? "stimulus-text stimulus-text-concealed" : "stimulus-text",
      stimulus.text ?? "",
    );
    surface.append(text);
  }

  if (overlay !== undefined) {
    surface.append(overlay);
  }

  return surface;
}

export function buildStimulusSurfaceOverlay(document: Document, title: string, detail: string) {
  const copy = createElement(document, "div", "stack-sm stimulus-surface-copy");
  const titleParagraph = createElement(document, "p", "section-title", title);
  const detailParagraph = createElement(document, "p", "muted", detail);

  copy.append(titleParagraph, detailParagraph);
  return copy;
}

export function buildStageFrame(
  document: Document,
  block: ResponseLabels,
  feedbackClassName: string,
  prefersTouchInput: boolean,
  stageStatusText: string,
  surface: HTMLElement,
  feedbackAnnouncement?: string,
  feedbackSymbol?: string,
  feedbackText?: string,
  responseControlsDisabled = false,
) {
  const section = createElement(document, "section", "stack session-stage");
  const feedback = createElement(document, "div", feedbackClassName);

  if (feedbackSymbol !== undefined) {
    const symbol = createElement(document, "span", "feedback-symbol", feedbackSymbol);
    feedback.append(symbol);
  }

  if (feedbackText !== undefined && feedbackText !== "") {
    const copy = createElement(document, "span", "feedback-copy", feedbackText);
    feedback.append(copy);
  }

  if (feedbackAnnouncement !== undefined) {
    feedback.setAttribute("role", "status");
    feedback.setAttribute("aria-live", "polite");

    const announcement = createElement(document, "span", "visually-hidden", feedbackAnnouncement);
    feedback.append(announcement);
  }

  const stageStatus = createElement(document, "p", "muted", stageStatusText);

  section.append(
    stageStatus,
    buildResponseHeaderGrid(document, block, prefersTouchInput, responseControlsDisabled),
    surface,
    feedback,
  );
  return section;
}

function buildResponseHeaderGrid(
  document: Document,
  block: ResponseLabels,
  prefersTouchInput: boolean,
  responseControlsDisabled: boolean,
) {
  const grid = createElement(document, "div", "label-grid response-label-grid");
  grid.append(
    buildLabelCard(
      document,
      "respond-left",
      false,
      block.left_labels,
      prefersTouchInput,
      responseControlsDisabled,
      "E",
    ),
    buildLabelCard(
      document,
      "respond-right",
      true,
      block.right_labels,
      prefersTouchInput,
      responseControlsDisabled,
      "I",
    ),
  );
  return grid;
}

function buildLabelCard(
  document: Document,
  action: "respond-left" | "respond-right",
  alignRight: boolean,
  labels: readonly string[],
  prefersTouchInput: boolean,
  responseControlsDisabled: boolean,
  side: "E" | "I",
) {
  const classNames = ["label-card", "stack-sm"];
  if (alignRight) {
    classNames.push("label-card-right");
  }

  const disabled = !prefersTouchInput || responseControlsDisabled;
  const card = createActionButton(document, action, classNames.join(" "), undefined, disabled);
  if (disabled) {
    card.setAttribute("aria-disabled", "true");
  }

  card.append(createSpan(document, "label-side", prefersTouchInput ? "Tap" : side));
  card.append(createSpan(document, "label-value", labels.join(" + ")));
  return card;
}

function createSpan(document: Document, className: string, textContent: string) {
  return createElement(document, "span", className, textContent);
}
