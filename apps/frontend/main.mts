import { startFrontend } from "./bootstrap.mjs";
import { createFrontendApiClient } from "./core/api_adapter.mjs";
import { FETCH_TIMEOUT_MS } from "./core/config.mjs";
import { resolveStartupConfiguration } from "./core/startup.mjs";

const pageUrl = new URL(window.location.href);
const { planSeed, sessionMode, startupError } = resolveStartupConfiguration(pageUrl);
startFrontend(createFrontendApiClient(FETCH_TIMEOUT_MS), sessionMode, planSeed, startupError);
