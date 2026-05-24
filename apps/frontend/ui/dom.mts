export function createActionButton(
  document: Document,
  action: string,
  className: string,
  textContent?: string,
  disabled = false,
  data?: Record<string, string>,
) {
  const button = createElement(document, "button", className, textContent);
  button.type = "button";
  button.dataset.action = action;
  button.disabled = disabled;

  if (data !== undefined) {
    for (const [key, value] of Object.entries(data)) {
      button.dataset[key] = value;
    }
  }

  return button;
}

export function createElement<K extends keyof HTMLElementTagNameMap>(
  document: Document,
  tagName: K,
  className?: string,
  textContent?: string,
): HTMLElementTagNameMap[K] {
  const element = document.createElement(tagName);

  if (className !== undefined) {
    element.className = className;
  }

  if (textContent !== undefined) {
    element.textContent = textContent;
  }

  return element;
}
