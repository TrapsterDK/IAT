import assert from "node:assert/strict";
import type { IncomingMessage, ServerResponse } from "node:http";
import type { TestContext } from "node:test";
import { test } from "node:test";

import { ResponseSide } from "../state/types.mjs";
import { createFrontendApiClient } from "./api_adapter.mjs";
import { listen } from "./testing/test_http.mjs";

const TIMEOUT_MS = 2_000;

test("createSession maps frontend request fields to API payload fields", async (testContext: TestContext) => {
  // Given: one server captures one session creation request body
  let requestBody = "";
  const server = await listen(async (request: IncomingMessage, response: ServerResponse<IncomingMessage>) => {
    for await (const chunk of request) {
      requestBody += chunk;
    }

    response.writeHead(201, { "content-type": "application/json" });
    response.end(JSON.stringify({ blocks: [], session_key: "session-1" }));
  });
  testContext.after(async () => {
    await server.close();
  });

  // When: the frontend adapter creates one session
  const api = createFrontendApiClient(TIMEOUT_MS, server.url);
  await api.createSession({
    clientContext: {
      devicePixelRatio: 2,
      platform: "linux",
      userAgent: "node-test",
      viewportHeightPx: 720,
      viewportWidthPx: 1280,
    },
    iatSlug: "demo",
  });

  // Then: the API request uses backend field names
  assert.deepEqual(JSON.parse(requestBody), {
    client_context: {
      device_pixel_ratio: 2,
      platform: "linux",
      user_agent: "node-test",
      viewport_height_px: 720,
      viewport_width_px: 1280,
    },
    iat_slug: "demo",
  });
});

test("completeBlock maps frontend event fields to API payload fields", async (testContext: TestContext) => {
  // Given: one server captures one completed block payload
  let requestBody = "";
  const server = await listen(async (request: IncomingMessage, response: ServerResponse<IncomingMessage>) => {
    for await (const chunk of request) {
      requestBody += chunk;
    }

    response.writeHead(204);
    response.end();
  });
  testContext.after(async () => {
    await server.close();
  });

  // When: the frontend adapter uploads one completed block
  const api = createFrontendApiClient(TIMEOUT_MS, server.url);
  await api.completeBlock("session-1", 2, {
    trials: [
      {
        events: [{ elapsedMs: 25, eventType: ResponseSide.Left }],
      },
    ],
  });

  // Then: the API request uses backend event field names
  assert.deepEqual(JSON.parse(requestBody), {
    trials: [
      {
        events: [{ elapsed_ms: 25, event_type: "left" }],
      },
    ],
  });
});

test("getScore maps backend score payload to the frontend score type", async (testContext: TestContext) => {
  // Given: one server returns one score payload
  const server = await listen(async (_request: IncomingMessage, response: ServerResponse<IncomingMessage>) => {
    response.writeHead(200, { "content-type": "application/json" });
    response.end(JSON.stringify({ d_score: 0.42, headline: "Result ready." }));
  });
  testContext.after(async () => {
    await server.close();
  });

  // When: the frontend adapter fetches one score
  const api = createFrontendApiClient(TIMEOUT_MS, server.url);
  const result = await api.getScore("session-1");

  // Then: the adapter returns the frontend-owned score shape
  if ("error" in result) {
    throw new Error("Expected one successful score response.");
  }

  assert.deepEqual(result.data, { d_score: 0.42, headline: "Result ready." });
});
