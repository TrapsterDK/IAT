import assert from "node:assert/strict";
import { text } from "node:stream/consumers";
import type { TestContext } from "node:test";
import { test } from "node:test";

import type { CompletedBlockRequest, CreateSessionRequest } from "@iat/apps/api/backend";
import { createApiClient } from "./api.mjs";
import { listen } from "./testing/test_http.mjs";

const TIMEOUT_MS = 20_000;

test("listIats sends a GET request to /iats", async (testContext: TestContext) => {
  // Given: one API server that returns one empty catalog
  const server = await listen(async (request, response) => {
    assert.equal(request.method, "GET");
    assert.equal(request.url, "/iats");
    assert.equal(await text(request), "");

    response.writeHead(200, { "content-type": "application/json" });
    response.end("[]");
  });
  testContext.after(async () => {
    await server.close();
  });

  // When: the catalog helper is called
  const api = createApiClient(TIMEOUT_MS, server.url);
  await api.listIats();
});

test("createSession sends a POST request to /api/sessions", async (testContext: TestContext) => {
  // Given: one session creation payload and one API server that accepts it
  const createSessionRequest: CreateSessionRequest = {
    client_context: {
      user_agent: "node-test",
    },
    iat_slug: "demo",
  };
  const server = await listen(async (request, response) => {
    assert.equal(request.method, "POST");
    assert.equal(request.url, "/api/sessions");
    assert.equal(await text(request), JSON.stringify(createSessionRequest));

    response.writeHead(201, { "content-type": "application/json" });
    response.end(JSON.stringify({ blocks: [], session_key: "session-1" }));
  });
  testContext.after(async () => {
    await server.close();
  });

  // When: the session creation helper is called
  const api = createApiClient(TIMEOUT_MS, server.url);
  await api.createSession(createSessionRequest);
});

test("completeBlock sends a PUT request to the block upload path", async (testContext: TestContext) => {
  // Given: one completed block payload and one API server that accepts it
  const completedBlockRequest: CompletedBlockRequest = {
    trials: [
      {
        events: [
          {
            elapsed_ms: 25,
            event_type: "left",
          },
        ],
      },
    ],
  };
  const server = await listen(async (request, response) => {
    assert.equal(request.method, "PUT");
    assert.equal(request.url, "/api/sessions/session-1/blocks/2");
    assert.equal(await text(request), JSON.stringify(completedBlockRequest));

    response.writeHead(204);
    response.end();
  });
  testContext.after(async () => {
    await server.close();
  });

  // When: the block upload helper is called
  const api = createApiClient(TIMEOUT_MS, server.url);
  await api.completeBlock("session-1", 2, completedBlockRequest);
});

test("getScore sends a GET request to the score path", async (testContext: TestContext) => {
  // Given: one API server that returns one score payload
  const server = await listen(async (request, response) => {
    assert.equal(request.method, "GET");
    assert.equal(request.url, "/api/sessions/session-1/score");
    assert.equal(await text(request), "");

    response.writeHead(200, { "content-type": "application/json" });
    response.end(JSON.stringify({ d_score: 0.42, summary: "Complete" }));
  });
  testContext.after(async () => {
    await server.close();
  });

  // When: the score helper is called
  const api = createApiClient(TIMEOUT_MS, server.url);
  await api.getScore("session-1");
});
