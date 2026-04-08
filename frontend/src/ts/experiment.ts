import { apiBaseUrl, fetchWithTimeout, parseTestListPayload, parseTestPayload } from "./api";
import { ExperimentRunner, getRunnerElements } from "./runner";
import type { AttemptSummary, CompletionResult, LandingTest, TestPayload } from "./types";

interface MessageAction {
  label: string;
  onClick: () => void;
  loadingLabel?: string;
}

interface AppElements {
  landingView: HTMLElement;
  runnerView: HTMLElement;
  summaryView: HTMLElement;
  testsList: HTMLElement;
  testTitle: HTMLElement;
  testDescription: HTMLElement;
  variantKeyMode: HTMLElement;
  summaryDescription: HTMLElement;
  summaryTrials: HTMLElement;
  summaryAccuracy: HTMLElement;
  summaryInitialRt: HTMLElement;
  summaryCompletedRt: HTMLElement;
  summaryVisibility: HTMLElement;
  restartButton: HTMLButtonElement;
}

function keyboardModeLabel(payload: TestPayload): string {
  const mode = payload.variant.keyEventMode === "keydown" ? "key press" : "key release";
  return `Keys ${payload.variant.keyboardShortcuts.left} and ${payload.variant.keyboardShortcuts.right} • ${mode}`;
}

function lookup<T extends HTMLElement>(selector: string): T {
  const element = document.querySelector<T>(selector);
  if (!element) {
    throw new Error(`Missing element ${selector}`);
  }
  return element;
}

function getAppElements(): AppElements {
  return {
    landingView: lookup("#landing-view"),
    runnerView: lookup("#runner-view"),
    summaryView: lookup("#summary-view"),
    testsList: lookup("#experiments-list"),
    testTitle: lookup("#experiment-title"),
    testDescription: lookup("#experiment-description"),
    variantKeyMode: lookup("#variant-key-mode"),
    summaryDescription: lookup("#summary-description"),
    summaryTrials: lookup("#summary-trials"),
    summaryAccuracy: lookup("#summary-accuracy"),
    summaryInitialRt: lookup("#summary-initial-rt"),
    summaryCompletedRt: lookup("#summary-completed-rt"),
    summaryVisibility: lookup("#summary-visibility"),
    restartButton: lookup<HTMLButtonElement>("#restart-button"),
  };
}

function showView(activeView: HTMLElement, elements: AppElements): void {
  [elements.landingView, elements.runnerView, elements.summaryView].forEach((view) => {
    view.classList.toggle("hidden", view !== activeView);
  });
}

function formatPercent(value: number): string {
  return `${(value * 100).toFixed(2)}%`;
}

function setSummary(
  result: CompletionResult,
  payload: TestPayload,
  elements: AppElements,
  diagnostics: { visibilityInterruptions: number },
): void {
  const summary: AttemptSummary = result.summary;
  elements.summaryDescription.textContent = `${payload.test.title} completed.`;
  elements.summaryTrials.textContent = String(summary.showingCount);
  elements.summaryAccuracy.textContent = formatPercent(summary.accuracy);
  elements.summaryInitialRt.textContent = `${summary.meanInitialReactionTimeMs} ms`;
  elements.summaryCompletedRt.textContent = `${summary.meanCompletedReactionTimeMs} ms`;
  elements.summaryVisibility.textContent = String(diagnostics.visibilityInterruptions);
}

function setRunnerMeta(payload: TestPayload, elements: AppElements): void {
  elements.testTitle.textContent = payload.test.title;
  elements.testDescription.textContent = payload.test.description;
  elements.variantKeyMode.textContent = keyboardModeLabel(payload);
}

function renderTestsMessage(elements: AppElements, title: string, description: string, action?: MessageAction): void {
  const card = document.createElement("article");
  card.className = "experiment-card";

  const titleElement = document.createElement("h2");
  titleElement.textContent = title;

  const descriptionElement = document.createElement("p");
  descriptionElement.textContent = description;

  card.append(titleElement, descriptionElement);

  if (action) {
    const button = document.createElement("button");
    button.className = "primary-button";
    button.type = "button";
    button.textContent = action.label;
    button.addEventListener("click", () => {
      if (button.disabled) {
        return;
      }

      if (action.loadingLabel) {
        setButtonLoadingState(button, true, action.loadingLabel);
      }

      try {
        action.onClick();
      } catch (error) {
        if (action.loadingLabel) {
          setButtonLoadingState(button, false, action.label);
        }
        throw error;
      }
    });
    card.append(button);
  }

  elements.testsList.replaceChildren(card);
}

function renderLoadingState(elements: AppElements, title: string, description: string): void {
  const card = document.createElement("article");
  card.className = "experiment-card loading-card";

  const spinner = document.createElement("span");
  spinner.className = "loading-spinner";
  spinner.setAttribute("aria-hidden", "true");

  const titleElement = document.createElement("h2");
  titleElement.textContent = title;

  const descriptionElement = document.createElement("p");
  descriptionElement.textContent = description;


  card.append(spinner, titleElement, descriptionElement);
  elements.testsList.replaceChildren(card);
}

function setButtonLoadingState(button: HTMLButtonElement, isLoading: boolean, label: string): void {
  button.disabled = isLoading;
  button.classList.toggle("is-loading", isLoading);
  button.textContent = label;
}

async function runTest(elements: AppElements, testSlug: string): Promise<void> {
  try {
    const payload = await createAttempt(testSlug);
    setRunnerMeta(payload, elements);
    showView(elements.runnerView, elements);

    const runner = new ExperimentRunner(payload, getRunnerElements());
    const result = await runner.run();
    setSummary(result, payload, elements, runner.getDiagnostics());
    showView(elements.summaryView, elements);
  } catch (error) {
    window.alert(error instanceof Error ? error.message : "Could not run the test.");
    showView(elements.landingView, elements);
  }
}

function createTestCard(test: LandingTest, elements: AppElements): HTMLElement {
  const article = document.createElement("article");
  article.className = "test-row";

  const copy = document.createElement("div");
  copy.className = "test-row-copy";
  const title = document.createElement("h2");
  title.textContent = test.title;
  const description = document.createElement("p");
  description.textContent = test.description;
  copy.append(title, description);

  const button = document.createElement("button");
  button.className = "start-button";
  button.type = "button";
  button.textContent = "Start";
  const defaultButtonLabel = button.textContent;

  button.addEventListener("click", () => {
    if (button.disabled) {
      return;
    }

    setButtonLoadingState(button, true, "Starting...");
    void runTest(elements, test.slug).finally(() => {
      setButtonLoadingState(button, false, defaultButtonLabel);
    });
  });

  article.append(copy, button);

  return article;
}

async function fetchTests(): Promise<LandingTest[]> {
  const response = await fetchWithTimeout(`${apiBaseUrl()}/tests`, undefined, {
    timeout: "Could not load tests because the server did not respond within 10 seconds.",
    network: "Could not load tests because the server is unavailable.",
  });
  if (!response.ok) {
    throw new Error("Could not load tests.");
  }

  const payload = parseTestListPayload(await response.json());
  return payload.tests;
}

async function createAttempt(testSlug: string): Promise<TestPayload> {
  const response = await fetchWithTimeout(
    `${apiBaseUrl()}/tests/${testSlug}/attempts`,
    {
      method: "POST",
    },
    {
      timeout: "Could not start the test because the server did not respond within 10 seconds.",
      network: "Could not start the test because the server is unavailable.",
    },
  );

  if (!response.ok) {
    throw new Error("Could not start the test.");
  }

  return parseTestPayload(await response.json());
}

async function renderTests(elements: AppElements): Promise<void> {
  renderLoadingState(elements, "Loading tests", "Checking whether the server is available.");

  try {
    const tests = await fetchTests();
    if (tests.length === 0) {
      renderTestsMessage(elements, "No tests are available", "Load the test definitions and refresh this page.");
      return;
    }

    elements.testsList.replaceChildren(...tests.map((test) => createTestCard(test, elements)));
  } catch (error) {
    const message = error instanceof Error ? error.message : "Could not load tests.";
    renderTestsMessage(elements, "Could not load tests", message, {
      label: "Retry",
      loadingLabel: "Retrying...",
      onClick: () => {
        void renderTests(elements);
      },
    });
  }
}

function bindRestart(elements: AppElements): void {
  elements.restartButton.addEventListener("click", async () => {
    showView(elements.landingView, elements);
    await renderTests(elements);
  });
}

async function main(): Promise<void> {
  const elements = getAppElements();
  bindRestart(elements);
  await renderTests(elements);
  showView(elements.landingView, elements);
}

void main();
