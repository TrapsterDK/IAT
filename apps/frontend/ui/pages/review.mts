import { PRELOAD_STALLED_AFTER_MS } from "../../core/config.mjs";
import { formatDuration } from "../../core/utils.mjs";
import { canAdvanceSession } from "../../state/block_uploads.mjs";
import type { IatCategory, IatStimulus, ReviewSessionState, RuntimeState } from "../../state/types.mjs";
import { buildProgressBar, buildSessionPage, createActionButton } from "../parts.mjs";

export function buildReviewPage(document: Document, runtime: RuntimeState, session: ReviewSessionState) {
  const canAdvance = canAdvanceSession(session);
  const hasPreloadFailures = session.preload.failures.length > 0;
  const section = document.createElement("section");
  section.className = "stack";

  const heading = document.createElement("h2");
  heading.className = "section-title";
  heading.textContent = "Before you start";

  const description = document.createElement("p");
  description.className = "muted";
  description.textContent = session.iatDetail.description;

  section.append(heading, description);

  const preloadSection = buildPreloadSection(document, session);
  if (preloadSection !== null) {
    section.append(preloadSection);
  }

  if (session.bootstrap.blocks.length > 0) {
    const toolbar = document.createElement("div");
    toolbar.className = "toolbar toolbar-end";
    toolbar.append(
      createActionButton(
        document,
        hasPreloadFailures ? "retry-preload" : "begin-test",
        "button button-primary",
        buildStartButtonLabel(canAdvance, hasPreloadFailures, session.preload.running),
        !isPrimaryActionEnabled(canAdvance, hasPreloadFailures, session.preload.running),
      ),
    );

    const reviewMessage = document.createElement("p");
    reviewMessage.className = "muted";
    reviewMessage.textContent = buildReviewMessage(canAdvance, hasPreloadFailures);

    section.append(
      reviewMessage,
      buildStimulusPreviewList(document, runtime, session.iatDetail.categories, canAdvance),
      toolbar,
    );
  }

  return buildSessionPage(document, session.iatDetail.title, section);
}

function buildPreloadSection(document: Document, session: ReviewSessionState) {
  const totalCount = session.preload.total;
  if (totalCount === 0 && session.preload.running !== true && session.preload.failures.length === 0) {
    return null;
  }

  const section = document.createElement("section");
  section.className = "stack stack-sm";
  const progressFraction = totalCount === 0 ? 1 : session.preload.loaded / totalCount;
  const progressValueText =
    totalCount === 0 ? "No images to preload." : `${session.preload.loaded} of ${totalCount} images loaded.`;
  const lastProgressAgeMs = Math.max(0, Date.now() - session.preload.lastProgressAt.getTime());

  const title = document.createElement("h3");
  title.className = "section-title";
  title.textContent = "Preparing the test";

  const message = document.createElement("p");
  message.className = "muted";
  message.textContent = buildPreloadMessage(session, lastProgressAgeMs);

  section.append(
    title,
    message,
    buildProgressBar(document, progressFraction, "Image preload progress", progressValueText),
  );

  return section;
}

function buildPreloadMessage(session: ReviewSessionState, lastProgressAgeMs: number) {
  if (session.preload.failures.length > 0 && !session.preload.running) {
    return "Some images did not load. Retry to continue.";
  }

  if (session.preload.running && session.preload.inFlightCount > 0) {
    if (lastProgressAgeMs >= PRELOAD_STALLED_AFTER_MS) {
      return `Still loading. Last progress was ${formatDuration(lastProgressAgeMs)} ago.`;
    }

    return "Preparing the test.";
  }

  if (canAdvanceSession(session)) {
    return "Ready to start.";
  }

  return "Preparing the test.";
}

function buildReviewMessage(canAdvance: boolean, hasPreloadFailures: boolean) {
  if (hasPreloadFailures) {
    return "Review the categories and retry image loading below.";
  }

  if (!canAdvance) {
    return "Review the categories while the test finishes preparing.";
  }

  return "Review the categories and stimuli below.";
}

function buildStartButtonLabel(canAdvance: boolean, hasPreloadFailures: boolean, preloadRunning: boolean) {
  if (hasPreloadFailures) {
    return preloadRunning ? "Loading..." : "Retry";
  }

  if (!canAdvance) {
    return "Preparing...";
  }

  return "Start";
}

function isPrimaryActionEnabled(canAdvance: boolean, hasPreloadFailures: boolean, preloadRunning: boolean) {
  if (hasPreloadFailures) {
    return !preloadRunning;
  }

  return canAdvance;
}

function buildStimulusPreviewList(
  document: Document,
  runtime: RuntimeState,
  categories: ReviewSessionState["iatDetail"]["categories"],
  showImagePreviews: boolean,
) {
  const previewList = document.createElement("div");

  for (const pair of categories) {
    for (const category of pair.category) {
      previewList.append(buildPreviewCategory(document, runtime, category, showImagePreviews));
    }
  }

  return previewList;
}

function buildPreviewCategory(
  document: Document,
  runtime: RuntimeState,
  category: IatCategory,
  showImagePreviews: boolean,
) {
  const column = document.createElement("section");
  column.className = "preview-category stack";

  const title = document.createElement("h3");
  title.className = "preview-category-title";
  title.textContent = category.label;

  const itemList = document.createElement("ul");
  itemList.className = "preview-stimulus-list";

  for (const [stimulusIndex, stimulus] of category.stimuli.entries()) {
    const item = document.createElement("li");
    item.append(buildStimulusPreview(document, runtime, category.label, stimulus, stimulusIndex, showImagePreviews));
    itemList.append(item);
  }

  column.append(title, itemList);
  return column;
}

function buildStimulusPreview(
  document: Document,
  runtime: RuntimeState,
  categoryLabel: string,
  stimulus: IatStimulus,
  stimulusIndex: number,
  showImagePreviews: boolean,
) {
  if (stimulus.text !== null) {
    return buildPreviewTag(document, stimulus.text);
  }

  const previewLabel = `${categoryLabel} ${stimulusIndex + 1}`;
  if (!showImagePreviews || stimulus.image_url === null) {
    return buildPreviewTag(document, previewLabel);
  }

  const imageObjectUrl = runtime.assets.imageObjectUrls.get(stimulus.image_url);
  if (imageObjectUrl === undefined) {
    return buildPreviewTag(document, previewLabel);
  }

  const image = document.createElement("img");
  image.className = "stimulus-thumb";
  image.alt = `${categoryLabel} stimulus ${stimulusIndex + 1}`;
  image.src = imageObjectUrl;
  return image;
}

function buildPreviewTag(document: Document, textContent: string) {
  const tag = document.createElement("span");
  tag.className = "preview-stimulus-tag";
  tag.textContent = textContent;
  return tag;
}
