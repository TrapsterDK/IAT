import assert from "node:assert/strict";
import type { TestContext } from "node:test";
import { test } from "node:test";

import { createRuntimeState } from "./runtime.mjs";

test("createRuntimeState copies browser capability flags into runtime state", (testContext: TestContext) => {
  // Given: one browser environment reports coarse touch input
  installBrowserGlobals(testContext, {
    coarsePointerMatches: true,
    maxTouchPoints: 3,
  });

  // When: the frontend runtime state is created
  const runtime = createRuntimeState();

  // Then: the runtime keeps browser capability flags and empty UI defaults
  assert.equal(runtime.device.prefersTouchInput, true);
  assert.deepEqual(runtime.catalog.items, []);
  assert.equal(runtime.catalog.error, null);
  assert.equal(runtime.catalog.loading, false);
  assert.equal(runtime.catalog.startingIatSlug, null);
  assert.equal(runtime.assets.imageObjectUrls.size, 0);
  assert.equal(runtime.session, null);
  assert.equal(runtime.ui.screenError, null);
});

test("createRuntimeState disables touch preference without browser touch support", (testContext: TestContext) => {
  // Given: one browser environment reports a coarse pointer but no touch points
  installBrowserGlobals(testContext, {
    coarsePointerMatches: true,
    maxTouchPoints: 0,
  });

  // When: the frontend runtime state is created
  const runtime = createRuntimeState();

  // Then: touch-first input is disabled even when the pointer media query is coarse
  assert.equal(runtime.device.prefersTouchInput, false);
});

function installBrowserGlobals(
  testContext: TestContext,
  browserState: { coarsePointerMatches: boolean; maxTouchPoints: number },
) {
  const navigatorDescriptor = Object.getOwnPropertyDescriptor(globalThis, "navigator");
  const windowDescriptor = Object.getOwnPropertyDescriptor(globalThis, "window");

  Object.defineProperty(globalThis, "navigator", {
    configurable: true,
    value: {
      maxTouchPoints: browserState.maxTouchPoints,
    } as unknown as Navigator,
  });
  Object.defineProperty(globalThis, "window", {
    configurable: true,
    value: {
      matchMedia: (query: string) => ({
        matches: query === "(pointer: coarse)" ? browserState.coarsePointerMatches : false,
      }),
    } as unknown as Window,
  });

  testContext.after(() => {
    restoreGlobalDescriptor("navigator", navigatorDescriptor);
    restoreGlobalDescriptor("window", windowDescriptor);
  });
}

function restoreGlobalDescriptor(propertyName: "navigator" | "window", descriptor: PropertyDescriptor | undefined) {
  if (descriptor === undefined) {
    Reflect.deleteProperty(globalThis, propertyName);
    return;
  }

  Object.defineProperty(globalThis, propertyName, descriptor);
}
