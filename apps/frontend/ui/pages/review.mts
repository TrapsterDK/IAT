import type { IatCategory, IatStimulus, ReviewSessionState } from "../../state/types.mjs";
import { buildSessionPage, createActionButton } from "../parts.mjs";

export function buildReviewPage(document: Document, session: ReviewSessionState) {
  const section = document.createElement("section");
  section.className = "stack";

  const heading = document.createElement("h2");
  heading.className = "section-title";
  heading.textContent = "Before you start";

  const description = document.createElement("p");
  description.className = "muted";
  description.textContent = session.iatDetail.description;

  section.append(heading, description);

  if (session.bootstrap.blocks.length > 0) {
    const toolbar = document.createElement("div");
    toolbar.className = "toolbar toolbar-end";
    toolbar.append(createActionButton(document, "begin-test", "button button-primary", "Start"));

    const reviewMessage = document.createElement("p");
    reviewMessage.className = "muted";
    reviewMessage.textContent = "Review the categories and stimuli below.";

    section.append(reviewMessage, buildStimulusPreviewList(document, session.iatDetail.categories), toolbar);
  }

  return buildSessionPage(document, session.iatDetail.title, section);
}

function buildStimulusPreviewList(document: Document, categories: ReviewSessionState["iatDetail"]["categories"]) {
  const previewList = document.createElement("div");

  for (const pair of categories) {
    for (const category of pair.category) {
      previewList.append(buildPreviewCategory(document, category));
    }
  }

  return previewList;
}

function buildPreviewCategory(document: Document, category: IatCategory) {
  const column = document.createElement("section");
  column.className = "preview-category stack";

  const title = document.createElement("h3");
  title.className = "preview-category-title";
  title.textContent = category.label;

  const itemList = document.createElement("ul");
  itemList.className = "preview-stimulus-list";

  for (const [stimulusIndex, stimulus] of category.stimuli.entries()) {
    const item = document.createElement("li");
    item.append(buildStimulusPreview(document, category.label, stimulus, stimulusIndex));
    itemList.append(item);
  }

  column.append(title, itemList);
  return column;
}

function buildStimulusPreview(document: Document, categoryLabel: string, stimulus: IatStimulus, stimulusIndex: number) {
  if (stimulus.text !== null) {
    const tag = document.createElement("span");
    tag.className = "preview-stimulus-tag";
    tag.textContent = stimulus.text;
    return tag;
  }

  if (stimulus.image_url === null) {
    const tag = document.createElement("span");
    tag.className = "preview-stimulus-tag";
    tag.textContent = `${categoryLabel} ${stimulusIndex + 1}`;
    return tag;
  }

  const image = document.createElement("img");
  image.className = "stimulus-thumb";
  image.alt = `${categoryLabel} stimulus ${stimulusIndex + 1}`;
  image.src = stimulus.image_url;
  return image;
}
