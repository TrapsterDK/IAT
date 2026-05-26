import type { CatalogItem, RuntimeState } from "../../state/types.mjs";
import { buildMessage, buildPageHeader, createActionButton } from "../parts.mjs";

export function buildCatalogPage(document: Document, runtime: RuntimeState) {
  const page = document.createElement("section");
  page.className = "page";
  page.append(buildPageHeader(document, "Implicit Association Test"));
  const { error, items, loading, startingIatSlug } = runtime.catalog;

  if (items.length === 0) {
    if (loading) {
      page.append(buildMessage(document, "Loading tests..."));
      return page;
    }

    if (error !== null) {
      page.append(buildMessage(document, error));
      return page;
    }

    page.append(buildMessage(document, "No tests are available right now."));
    return page;
  }

  if (error !== null) {
    page.append(buildMessage(document, error));
  }

  const list = document.createElement("div");
  for (const iat of items) {
    list.append(buildCatalogItem(document, iat, startingIatSlug));
  }

  page.append(list);
  return page;
}

function buildCatalogItem(document: Document, iat: CatalogItem, startingIatSlug: string | null) {
  const isStarting = startingIatSlug === iat.slug;
  const item = document.createElement("article");
  item.className = "catalog-item";

  const copy = document.createElement("div");
  copy.className = "stack stack-sm";

  const title = document.createElement("h2");
  title.className = "section-title";
  title.textContent = iat.title;

  const description = document.createElement("p");
  description.className = "muted";
  description.textContent = iat.description;

  copy.append(title, description);

  const actions = document.createElement("div");
  actions.className = "toolbar toolbar-end";
  actions.append(
    createActionButton(
      document,
      "start-session",
      "button button-primary",
      isStarting ? "Starting..." : "Start",
      isStarting,
      { slug: iat.slug },
    ),
  );

  item.append(copy, actions);
  return item;
}
