import { createFrontendApiClient } from "./core/api_adapter.mjs";
import { FETCH_TIMEOUT_MS } from "./core/config.mjs";
import { bindAppController } from "./controller.mjs";
import { createBrowserSessionFlowEnvironment, createSessionFlow } from "./session/flow.mjs";
import { createRuntimeState } from "./state/runtime.mjs";
import { render } from "./ui/render.mjs";

const appRoot = document.querySelector<HTMLElement>("#app");

if (appRoot === null) {
  throw new Error("App root element not found");
}

const runtime = createRuntimeState();
const renderApp = () => render(appRoot, runtime);
const sessionFlow = createSessionFlow(
  runtime,
  renderApp,
  createFrontendApiClient(FETCH_TIMEOUT_MS),
  createBrowserSessionFlowEnvironment(),
);
bindAppController(appRoot, document, renderApp, runtime, sessionFlow);
renderApp();
void sessionFlow.fetchCatalog();
