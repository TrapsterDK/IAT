import { bindAppController } from "./controller.mjs";
import type { FrontendApiClient } from "./core/api_adapter.mjs";
import { render } from "./render.mjs";
import { createBrowserSessionFlowEnvironment, createSessionFlow } from "./session/flow.mjs";
import { createRuntimeState } from "./state/runtime.mjs";
import type { SessionMode } from "./state/types.mjs";

export function startFrontend(
  api: FrontendApiClient,
  sessionMode: SessionMode | null,
  planSeed: number | null,
  startupError: string | null,
) {
  const appRoot = document.querySelector<HTMLElement>("#app");

  if (appRoot === null) {
    throw new Error("App root element not found");
  }

  const runtime = createRuntimeState();
  runtime.ui.screenError = startupError;
  const renderApp = () => render(appRoot, runtime);
  const sessionFlow = createSessionFlow(
    runtime,
    renderApp,
    api,
    createBrowserSessionFlowEnvironment(),
    sessionMode,
    planSeed,
  );
  bindAppController(appRoot, document, renderApp, runtime, sessionFlow);
  renderApp();
  void sessionFlow.fetchCatalog();
}
