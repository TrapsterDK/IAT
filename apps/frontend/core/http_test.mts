import assert from "node:assert/strict";
import type { TestContext } from "node:test";
import { test } from "node:test";

import { fetchResponseWithTimeout } from "./http.mjs";
import { listen } from "./testing/test_http.mjs";

test("fetchResponseWithTimeout returns the response before the timeout", async (testContext: TestContext) => {
  // Given: a server that responds immediately and a request with a generous timeout
  const server = await listen((_request, response) => {
    response.writeHead(200, { "content-type": "text/plain" });
    response.end("ok");
  });
  testContext.after(async () => {
    await server.close();
  });
  const request = new Request(server.url);

  // When: the request is fetched through the timeout wrapper
  const response = await fetchResponseWithTimeout(request, 100);

  // Then: the successful response is returned unchanged
  assert.equal(response.status, 200);
  assert.equal(await response.text(), "ok");
});

test("fetchResponseWithTimeout rejects when the timeout elapses first", async (testContext: TestContext) => {
  // Given: a server that responds too slowly for the configured timeout
  const server = await listen((_request, response) => {
    globalThis.setTimeout(() => {
      response.writeHead(200, { "content-type": "text/plain" });
      response.end("slow");
    }, 50);
  });
  testContext.after(async () => {
    await server.close();
  });
  const request = new Request(server.url);

  // When: the request is fetched with a short timeout
  await assert.rejects(fetchResponseWithTimeout(request, 10), {
    message: "The request timed out.",
  });

  // Then: the timeout error is surfaced
  assert.ok(true);
});
