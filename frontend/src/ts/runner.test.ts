import { describe, expect, it } from "vitest";

import { buildShowingPlan } from "./runner";
import type { TestPayload } from "./types";

const payload: TestPayload = {
  attempt: {
    publicId: "attempt-1",
    seed: 123,
    attemptToken: "token-1",
  },
  test: {
    slug: "demo",
    title: "Demo",
    description: "Demo",
  },
  variant: {
    keyEventMode: "keydown",
    keyboardShortcuts: {
      left: "E",
      right: "I",
    },
    preloadAssets: true,
    interTrialIntervalMs: 150,
    responseTimeoutMs: 5000,
  },
  categories: [
    { id: 1, code: "flowers", label: "Flowers" },
    { id: 2, code: "insects", label: "Insects" },
  ],
  stimuliByCategory: {
    "1": [
      { id: 11, contentType: "text", textValue: "rose", assetPath: null },
      { id: 12, contentType: "text", textValue: "tulip", assetPath: null },
    ],
    "2": [
      { id: 21, contentType: "text", textValue: "ant", assetPath: null },
      { id: 22, contentType: "text", textValue: "gnat", assetPath: null },
    ],
  },
  phases: [
    {
      id: 1,
      sequenceNumber: 1,
      showingsPerCategory: 2,
      categories: {
        left: [{ id: 1, label: "Flowers" }],
        right: [{ id: 2, label: "Insects" }],
      },
    },
  ],
};

describe("buildShowingPlan", () => {
  it("builds a deterministic balanced plan", () => {
    const firstPlan = buildShowingPlan(payload);
    const secondPlan = buildShowingPlan(payload);

    expect(firstPlan).toEqual(secondPlan);
    expect(firstPlan).toHaveLength(4);
    expect(firstPlan.filter((showing) => showing.expectedSide === "left")).toHaveLength(2);
    expect(firstPlan.filter((showing) => showing.expectedSide === "right")).toHaveLength(2);
  });
});
