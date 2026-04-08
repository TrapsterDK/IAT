import { apiBaseUrl, fetchWithTimeout, parseCompletionResult } from "./api";
import type {
  CompletionPayload,
  CompletionResult,
  PhaseCategorySummary,
  PhaseSummary,
  PlannedShowing,
  ShowingInput,
  ShowingResult,
  Side,
  StimulusSummary,
  TestPayload,
} from "./types";

function assetUrl(path: string): string {
  if (/^https?:\/\//.test(path)) {
    return path;
  }

  const apiUrl = new URL(apiBaseUrl(), window.location.origin);
  return new URL(path, `${apiUrl.origin}/`).toString();
}

function mulberry32(seed: number): () => number {
  let state = seed >>> 0;
  return () => {
    state += 0x6d2b79f5;
    let value = Math.imul(state ^ (state >>> 15), 1 | state);
    value ^= value + Math.imul(value ^ (value >>> 7), 61 | value);
    return ((value ^ (value >>> 14)) >>> 0) / 4294967296;
  };
}

function shuffleInPlace<T>(items: T[], random: () => number): T[] {
  for (let index = items.length - 1; index > 0; index -= 1) {
    const swapIndex = Math.floor(random() * (index + 1));
    [items[index], items[swapIndex]] = [items[swapIndex], items[index]];
  }
  return items;
}

function categoryKey(categoryId: number): string {
  return String(categoryId);
}

function labelCategories(categories: PhaseCategorySummary[]): string {
  return categories.map((category) => category.label).join(" or ");
}

function keyboardShortcutHint(payload: TestPayload): string {
  return `${payload.variant.keyboardShortcuts.left} for left and ${payload.variant.keyboardShortcuts.right} for right`;
}

function phaseTitle(phase: PhaseSummary): string {
  return `Phase ${phase.sequenceNumber}`;
}

function phaseInstructions(phase: PhaseSummary): string {
  const leftLabels = phase.categories.left.map((category) => category.label).join(" or ");
  const rightLabels = phase.categories.right.map((category) => category.label).join(" or ");

  return `Press left for ${leftLabels}. Press right for ${rightLabels}.`;
}

function sortPhases(left: PhaseSummary, right: PhaseSummary): number {
  return left.sequenceNumber - right.sequenceNumber;
}

function randomizedStimuli(stimuli: StimulusSummary[], count: number, random: () => number): StimulusSummary[] {
  const selected: StimulusSummary[] = [];
  while (selected.length < count) {
    selected.push(...shuffleInPlace([...stimuli], random));
  }
  return selected.slice(0, count);
}

function stimulusLabel(stimulus: StimulusSummary): string {
  if (stimulus.contentType === "text") {
    if (stimulus.textValue === null) {
      throw new Error(`Text stimulus ${stimulus.id} is missing text content.`);
    }
    return stimulus.textValue;
  }
  if (stimulus.assetPath === null) {
    throw new Error(`Image stimulus ${stimulus.id} is missing an asset path.`);
  }
  return stimulus.assetPath;
}

function buildSideShowings(
  categoryIds: PhaseCategorySummary[],
  payload: TestPayload,
  countPerCategory: number,
  side: Side,
  phaseId: number,
  phaseIndex: number,
  random: () => number,
): PlannedShowing[] {
  const showings: PlannedShowing[] = [];
  const allowedLeftCategories = side === "left" ? categoryIds : [];
  const allowedRightCategories = side === "right" ? categoryIds : [];

  categoryIds.forEach((category) => {
    const stimuli = payload.stimuliByCategory[categoryKey(category.id)] ?? [];
    if (stimuli.length === 0) {
      throw new Error(`Category ${category.label} does not have any stimuli.`);
    }

    const selectedStimuli = randomizedStimuli(stimuli, countPerCategory, random);
    selectedStimuli.forEach((stimulus) => {
      showings.push({
        phaseId,
        phaseIndex,
        showingIndex: -1,
        stimulusId: stimulus.id,
        stimulusLabel: stimulusLabel(stimulus),
        stimulusAssetPath: stimulus.assetPath,
        expectedSide: side,
        allowedLeftCategories,
        allowedRightCategories,
      });
    });
  });

  return showings;
}

export function buildShowingPlan(payload: TestPayload): PlannedShowing[] {
  const random = mulberry32(payload.attempt.seed);
  const plan: PlannedShowing[] = [];
  const phases = [...payload.phases].sort(sortPhases);

  phases.forEach((phase, phaseIndex) => {
    const leftShowings = buildSideShowings(
      phase.categories.left,
      payload,
      phase.showingsPerCategory,
      "left",
      phase.id,
      phaseIndex,
      random,
    );
    const rightShowings = buildSideShowings(
      phase.categories.right,
      payload,
      phase.showingsPerCategory,
      "right",
      phase.id,
      phaseIndex,
      random,
    );
    const phaseShowings = shuffleInPlace([...leftShowings, ...rightShowings], random);

    phaseShowings.forEach((showing, showingIndex) => {
      plan.push({
        ...showing,
        showingIndex,
        allowedLeftCategories: phase.categories.left,
        allowedRightCategories: phase.categories.right,
      });
    });
  });

  return plan;
}

function sleep(milliseconds: number): Promise<void> {
  return new Promise((resolve) => {
    window.setTimeout(resolve, milliseconds);
  });
}

const OVERLAY_COUNTDOWN_SECONDS = 3;

function setButtonLoadingState(button: HTMLButtonElement, isLoading: boolean, label: string): void {
  button.disabled = isLoading;
  button.classList.toggle("is-loading", isLoading);
  button.textContent = label;
}

async function preloadAssets(plan: PlannedShowing[]): Promise<void> {
  const imagePaths = [
    ...new Set(plan.map((showing) => showing.stimulusAssetPath).filter((path): path is string => Boolean(path))),
  ];

  await Promise.all(
    imagePaths.map(
      (path) =>
        new Promise<void>((resolve, reject) => {
          const image = new Image();
          image.onload = () => resolve();
          image.onerror = () => reject(new Error(`Could not preload ${path}`));
          image.src = assetUrl(path);
        }),
    ),
  );
}

interface RunnerElements {
  overlay: HTMLElement;
  overlayTitle: HTMLElement;
  overlayDescription: HTMLElement;
  overlayHint: HTMLElement;
  overlayCountdown: HTMLElement;
  overlayAction: HTMLButtonElement;
  leftLabel: HTMLElement;
  rightLabel: HTMLElement;
  stimulus: HTMLElement;
  errorIndicator: HTMLElement;
  leftButton: HTMLButtonElement;
  rightButton: HTMLButtonElement;
  statusText: HTMLElement;
  progressText: HTMLElement;
}

interface RecordedInput {
  side: Side;
  inputSource: "keyboard" | "button";
  eventTimestampMs: number;
  handlerTimestampMs: number;
}

interface RunnerDiagnostics {
  visibilityInterruptions: number;
}

function nextFrame(): Promise<number> {
  return new Promise((resolve) => {
    window.requestAnimationFrame(() => {
      resolve(performance.now());
    });
  });
}

export class ExperimentRunner {
  private readonly phases: PhaseSummary[];
  private readonly plan: PlannedShowing[];
  private readonly showings: ShowingResult[] = [];
  private readonly cleanupTasks: Array<() => void> = [];
  private visibilityInterruptions = 0;

  constructor(
    private readonly payload: TestPayload,
    private readonly elements: RunnerElements,
  ) {
    this.phases = [...payload.phases].sort(sortPhases);
    this.plan = buildShowingPlan({
      ...payload,
      phases: this.phases,
    });
  }

  public getDiagnostics(): RunnerDiagnostics {
    return {
      visibilityInterruptions: this.visibilityInterruptions,
    };
  }

  public async run(): Promise<CompletionResult> {
    this.bindDiagnostics();

    try {
      if (this.payload.variant.preloadAssets) {
        this.elements.statusText.textContent = "Loading images";
        await preloadAssets(this.plan);
      }

      for (let planIndex = 0; planIndex < this.plan.length; planIndex += 1) {
        const showing = this.plan[planIndex];
        const phase = this.phases[showing.phaseIndex];

        if (planIndex === 0 || this.plan[planIndex - 1].phaseId !== showing.phaseId) {
          this.renderLabels(showing.allowedLeftCategories, showing.allowedRightCategories);
          await this.showInstructionOverlay(
            phaseTitle(phase),
            `${phaseInstructions(phase)} Press Space when you are ready.`,
            {
              hintText: "Press Space to start",
              countdownPrefix: "Starting in",
            },
          );
        } else {
          this.renderLabels(showing.allowedLeftCategories, showing.allowedRightCategories);
        }

        this.elements.statusText.textContent = phaseTitle(phase);
        this.elements.progressText.textContent = `${planIndex + 1} / ${this.plan.length}`;
        this.elements.errorIndicator.classList.remove("visible");

        const onset = await this.renderShowing(showing);
        const result = await this.captureShowingResult(showing, onset);
        this.showings.push(result);

        await sleep(this.payload.variant.interTrialIntervalMs);
      }

      this.clearStimulus();
      return this.uploadResultsWithRetry();
    } finally {
      this.cleanupDiagnostics();
    }
  }

  private bindDiagnostics(): void {
    const visibilityHandler = () => {
      if (document.visibilityState === "hidden") {
        this.visibilityInterruptions += 1;
      }
    };
    document.addEventListener("visibilitychange", visibilityHandler);
    this.cleanupTasks.push(() => {
      document.removeEventListener("visibilitychange", visibilityHandler);
    });
  }

  private cleanupDiagnostics(): void {
    while (this.cleanupTasks.length > 0) {
      const cleanup = this.cleanupTasks.pop();
      cleanup?.();
    }
  }

  private renderLabels(leftCategories: PhaseCategorySummary[], rightCategories: PhaseCategorySummary[]): void {
    this.elements.leftLabel.textContent = `${this.payload.variant.keyboardShortcuts.left}: ${labelCategories(leftCategories)}`;
    this.elements.rightLabel.textContent = `${this.payload.variant.keyboardShortcuts.right}: ${labelCategories(rightCategories)}`;
  }

  private clearStimulus(): void {
    this.elements.stimulus.textContent = "";
  }

  private buildCompletionPayload(): CompletionPayload {
    return {
      attemptToken: this.payload.attempt.attemptToken,
      environment: {
        userAgent: navigator.userAgent,
        platform: navigator.platform,
        language: navigator.language,
        viewportWidth: window.innerWidth,
        viewportHeight: window.innerHeight,
        devicePixelRatio: window.devicePixelRatio,
        visibilityInterruptions: this.visibilityInterruptions,
      },
      showings: this.showings,
    };
  }

  private async uploadResults(): Promise<CompletionResult> {
    this.elements.statusText.textContent = "Uploading results";
    const response = await fetchWithTimeout(
      `${apiBaseUrl()}/attempts/${this.payload.attempt.publicId}/complete`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(this.buildCompletionPayload()),
      },
      {
        timeout:
          "Could not save experiment results because the server did not respond within 10 seconds. Keep this tab open and retry the upload.",
        network:
          "Could not save experiment results because the server is unavailable. Keep this tab open and retry the upload.",
      },
    );

    if (!response.ok) {
      throw new Error("Could not save experiment results. Keep this tab open and retry the upload.");
    }

    return parseCompletionResult(await response.json());
  }

  private async uploadResultsWithRetry(): Promise<CompletionResult> {
    while (true) {
      try {
        this.showLoadingOverlay(
          "Uploading results",
          "Saving your responses. This request will time out after 10 seconds.",
        );
        return await this.uploadResults();
      } catch (error) {
        this.hideOverlay();
        const message = error instanceof Error ? error.message : "Could not save your results.";
        await this.showOverlay("Save failed", message, "Retry", {
          loadingLabel: "Retrying...",
          keepVisibleOnAction: true,
        });
      }
    }
  }

  private renderStimulus(showing: PlannedShowing): void {
    if (showing.stimulusAssetPath) {
      const image = document.createElement("img");
      image.alt = "stimulus";
      image.src = assetUrl(showing.stimulusAssetPath);
      this.elements.stimulus.replaceChildren(image);
      return;
    }
    this.elements.stimulus.textContent = showing.stimulusLabel;
  }

  private async renderShowing(showing: PlannedShowing): Promise<number> {
    this.renderStimulus(showing);
    return nextFrame();
  }

  private async showOverlay(
    title: string,
    description: string,
    actionText: string,
    options?: { loadingLabel?: string; keepVisibleOnAction?: boolean },
  ): Promise<void> {
    this.elements.overlayTitle.textContent = title;
    this.elements.overlayDescription.textContent = description;
    this.elements.overlayHint.classList.add("hidden");
    this.elements.overlayCountdown.classList.add("hidden");
    this.elements.overlayCountdown.textContent = "";
    this.elements.overlayAction.classList.remove("hidden");
    setButtonLoadingState(this.elements.overlayAction, false, actionText);
    this.elements.overlay.classList.remove("hidden");

    await new Promise<void>((resolve) => {
      const clickHandler = () => {
        this.elements.overlayAction.removeEventListener("click", clickHandler);
        if (options?.loadingLabel) {
          setButtonLoadingState(this.elements.overlayAction, true, options.loadingLabel);
        }
        if (!options?.keepVisibleOnAction) {
          this.hideOverlay();
        }
        resolve();
      };
      this.elements.overlayAction.addEventListener("click", clickHandler, { once: true });
    });
  }

  private showLoadingOverlay(title: string, description: string): void {
    this.elements.overlayTitle.textContent = title;
    this.elements.overlayDescription.textContent = description;
    this.elements.overlayHint.classList.add("hidden");
    this.elements.overlayCountdown.classList.add("hidden");
    this.elements.overlayCountdown.textContent = "";
    this.elements.overlayAction.classList.remove("hidden");
    setButtonLoadingState(this.elements.overlayAction, true, "Working...");
    this.elements.overlay.classList.remove("hidden");
  }

  private hideOverlay(): void {
    this.elements.overlay.classList.add("hidden");
  }

  private async captureShowingResult(showing: PlannedShowing, stimulusOnsetMs: number): Promise<ShowingResult> {
    let currentStimulusOnsetMs = stimulusOnsetMs;

    while (true) {
      const inputs: ShowingInput[] = [];

      while (true) {
        const input = await this.waitForInput(this.payload.variant.responseTimeoutMs);
        if (input === null) {
          break;
        }

        inputs.push({
          inputIndex: inputs.length,
          side: input.side,
          inputSource: input.inputSource,
          eventTimestampMs: input.eventTimestampMs,
          handlerTimestampMs: input.handlerTimestampMs,
        });

        if (input.side === showing.expectedSide) {
          return {
            phaseId: showing.phaseId,
            stimulusId: showing.stimulusId,
            showingIndex: showing.showingIndex,
            stimulusOnsetMs: currentStimulusOnsetMs,
            inputs,
          };
        }

        this.elements.errorIndicator.classList.add("visible");
      }

      this.elements.errorIndicator.classList.remove("visible");
      await this.showInstructionOverlay(
        "Time ran out",
        `No response was recorded within ${this.payload.variant.responseTimeoutMs} ms. The same item will be shown again after a 3 second countdown.`,
        {
          hintText: "Press Space to continue",
          countdownPrefix: "Restarting in",
        },
      );
      currentStimulusOnsetMs = await this.renderShowing(showing);
    }
  }

  private async showInstructionOverlay(
    title: string,
    description: string,
    options: { hintText: string; countdownPrefix: string },
  ): Promise<void> {
    this.elements.statusText.textContent = title;
    this.elements.overlayTitle.textContent = title;
    this.elements.overlayDescription.textContent = description;
    this.elements.overlayHint.textContent = options.hintText;
    this.elements.overlayHint.classList.remove("hidden");
    this.elements.overlayCountdown.classList.add("hidden");
    this.elements.overlayCountdown.textContent = "";
    this.elements.overlayAction.classList.add("hidden");
    this.elements.overlay.classList.remove("hidden");

    await new Promise<void>((resolve) => {
      const keyHandler = (event: KeyboardEvent) => {
        if (event.repeat || event.code !== "Space") {
          return;
        }

        event.preventDefault();
        document.removeEventListener("keydown", keyHandler);
        void this.runOverlayCountdown(resolve, options.countdownPrefix);
      };

      document.addEventListener("keydown", keyHandler);
    });
  }

  private async runOverlayCountdown(onComplete: () => void, countdownPrefix: string): Promise<void> {
    this.elements.overlayHint.classList.add("hidden");
    this.elements.overlayCountdown.classList.remove("hidden");

    for (let seconds = OVERLAY_COUNTDOWN_SECONDS; seconds > 0; seconds -= 1) {
      this.elements.statusText.textContent = `${countdownPrefix} ${seconds}`;
      this.elements.overlayCountdown.textContent = `${countdownPrefix} ${seconds}`;
      await sleep(1000);
    }

    this.hideOverlay();
    onComplete();
  }

  private waitForInput(timeoutMs: number): Promise<RecordedInput | null> {
    return new Promise((resolve) => {
      const cleanupHandlers: Array<() => void> = [];
      let finished = false;

      const finish = (input: RecordedInput | null) => {
        if (finished) {
          return;
        }
        finished = true;
        cleanupHandlers.forEach((cleanup) => cleanup());
        resolve(input);
      };

      const timeoutId = window.setTimeout(() => {
        finish(null);
      }, timeoutMs);
      cleanupHandlers.push(() => {
        window.clearTimeout(timeoutId);
      });

      const eventName = this.payload.variant.keyEventMode;
      const keyboardHandler = (event: KeyboardEvent) => {
        if (event.repeat) {
          return;
        }
        const side = this.sideFromKeyboardEvent(event);
        if (!side) {
          return;
        }
        event.preventDefault();
        finish({
          side,
          inputSource: "keyboard",
          eventTimestampMs: event.timeStamp,
          handlerTimestampMs: performance.now(),
        });
      };

      document.addEventListener(eventName, keyboardHandler);
      cleanupHandlers.push(() => document.removeEventListener(eventName, keyboardHandler));

      const bindButton = (button: HTMLButtonElement, side: Side) => {
        const clickHandler = () => {
          finish({
            side,
            inputSource: "button",
            eventTimestampMs: performance.now(),
            handlerTimestampMs: performance.now(),
          });
        };
        button.addEventListener("click", clickHandler);
        cleanupHandlers.push(() => button.removeEventListener("click", clickHandler));
      };

      bindButton(this.elements.leftButton, "left");
      bindButton(this.elements.rightButton, "right");
    });
  }

  private sideFromKeyboardEvent(event: KeyboardEvent): Side | null {
    const normalizedKey = event.key.toLowerCase();
    if (normalizedKey === this.payload.variant.keyboardShortcuts.left.toLowerCase()) {
      return "left";
    }
    if (normalizedKey === this.payload.variant.keyboardShortcuts.right.toLowerCase()) {
      return "right";
    }
    return null;
  }
}

export function getRunnerElements(root: ParentNode = document): RunnerElements {
  const lookup = <T extends HTMLElement>(id: string): T => {
    const element = root.querySelector<T>(`#${id}`);
    if (!element) {
      throw new Error(`Missing element #${id}`);
    }
    return element;
  };

  return {
    overlay: lookup("overlay"),
    overlayTitle: lookup("overlay-title"),
    overlayDescription: lookup("overlay-description"),
    overlayHint: lookup("overlay-hint"),
    overlayCountdown: lookup("overlay-countdown"),
    overlayAction: lookup<HTMLButtonElement>("overlay-action"),
    leftLabel: lookup("left-label"),
    rightLabel: lookup("right-label"),
    stimulus: lookup("stimulus"),
    errorIndicator: lookup("error-indicator"),
    leftButton: lookup<HTMLButtonElement>("left-button"),
    rightButton: lookup<HTMLButtonElement>("right-button"),
    statusText: lookup("status-text"),
    progressText: lookup("progress-text"),
  };
}
