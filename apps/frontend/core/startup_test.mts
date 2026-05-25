import assert from "node:assert/strict";
import { test } from "node:test";

import { resolvePlanSeed, resolveSessionMode, resolveStartupConfiguration } from "./startup.mjs";

test("resolvePlanSeed keeps the main app route free of deterministic startup seeds", () => {
  // Given: one participant-facing frontend URL.
  const url = new URL("https://example.test/");

  // When: the startup plan seed is resolved.
  const planSeed = resolvePlanSeed(url);

  // Then: no deterministic startup seed is produced.
  assert.equal(planSeed, null);
});

test("resolvePlanSeed parses deterministic evaluation seeds", () => {
  // Given: one shared frontend URL with one deterministic plan seed.
  const url = new URL("https://example.test/?plan_seed=123");

  // When: the startup plan seed is resolved.
  const planSeed = resolvePlanSeed(url);

  // Then: the deterministic plan seed is preserved.
  assert.equal(planSeed, 123);
});

test("resolvePlanSeed rejects invalid plan seeds", () => {
  // Given: one evaluation URL with one invalid deterministic plan seed.
  const url = new URL("https://example.test/?session_mode=evaluation&plan_seed=abc");

  // When: the startup plan seed is resolved.
  // Then: the invalid plan seed is rejected.
  assert.throws(() => resolvePlanSeed(url), /Expected one non-negative integer 'plan_seed' query parameter\./);
});

test("resolvePlanSeed rejects duplicate plan seeds", () => {
  // Given: one evaluation URL with duplicate deterministic plan seeds.
  const url = new URL("https://example.test/?session_mode=evaluation&plan_seed=123&plan_seed=456");

  // When: the startup plan seed is resolved.
  // Then: startup rejects the ambiguous plan seed.
  assert.throws(() => resolvePlanSeed(url), /Expected at most one 'plan_seed' query parameter\./);
});

test("resolveSessionMode keeps the main app route free of startup session overrides", () => {
  // Given: one participant-facing frontend URL without one deterministic plan seed.
  const url = new URL("https://example.test/");

  // When: the startup session mode is resolved.
  const sessionMode = resolveSessionMode(url);

  // Then: no startup session mode override is produced.
  assert.equal(sessionMode, null);
});

test("resolveSessionMode only parses the session_mode query parameter", () => {
  // Given: one shared frontend URL with one participant mode and one deterministic plan seed.
  const url = new URL("https://example.test/?session_mode=participant&plan_seed=123");

  // When: the startup session mode is resolved.
  const sessionMode = resolveSessionMode(url);

  // Then: the resolver preserves the explicit session mode without validating other parameters.
  assert.equal(sessionMode, "participant");
});

test("resolveSessionMode parses explicit evaluation mode", () => {
  // Given: one shared frontend URL with one explicit evaluation-mode query.
  const url = new URL("https://example.test/?session_mode=evaluation");

  // When: the startup session mode is resolved.
  const sessionMode = resolveSessionMode(url);

  // Then: the explicit evaluation mode is preserved.
  assert.equal(sessionMode, "evaluation");
});

test("resolveSessionMode rejects duplicate session modes", () => {
  // Given: one shared frontend URL with duplicate session-mode query parameters.
  const url = new URL("https://example.test/?session_mode=participant&session_mode=evaluation");

  // When: the startup session mode is resolved.
  // Then: startup rejects the ambiguous session mode.
  assert.throws(() => resolveSessionMode(url), /Expected at most one 'session_mode' query parameter\./);
});

test("resolveSessionMode rejects unsupported session modes", () => {
  // Given: one shared frontend URL with one unsupported session mode query.
  const url = new URL("https://example.test/?session_mode=benchmark");

  // When: the startup session mode is resolved.
  // Then: startup rejects the unsupported session mode.
  assert.throws(() => resolveSessionMode(url), /Expected 'session_mode' to be 'participant' or 'evaluation'\./);
});

test("resolveStartupConfiguration infers evaluation mode from one plan seed", () => {
  // Given: one shared frontend URL with one deterministic plan seed but no explicit session mode.
  const url = new URL("https://example.test/?plan_seed=123");

  // When: the startup configuration is resolved.
  const startupConfiguration = resolveStartupConfiguration(url);

  // Then: deterministic evaluation mode is inferred from the plan seed.
  assert.deepEqual(startupConfiguration, {
    planSeed: 123,
    sessionMode: "evaluation",
    startupError: null,
  });
});

test("resolveStartupConfiguration preserves explicit participant mode without a plan seed", () => {
  // Given: one shared frontend URL that explicitly stays in participant mode.
  const url = new URL("https://example.test/?session_mode=participant");

  // When: the startup configuration is resolved.
  const startupConfiguration = resolveStartupConfiguration(url);

  // Then: the explicit participant mode is preserved.
  assert.deepEqual(startupConfiguration, {
    planSeed: null,
    sessionMode: "participant",
    startupError: null,
  });
});

test("resolveStartupConfiguration converts invalid evaluation queries into one startup error", () => {
  // Given: one shared frontend URL with one invalid participant-only query combination.
  const url = new URL("https://example.test/?session_mode=participant&plan_seed=123");

  // When: the startup configuration is resolved.
  const startupConfiguration = resolveStartupConfiguration(url);

  // Then: startup session overrides are cleared and the UI receives one startup error message.
  assert.deepEqual(startupConfiguration, {
    planSeed: null,
    sessionMode: null,
    startupError: "Expected 'session_mode' to be 'evaluation' when 'plan_seed' is set.",
  });
});
