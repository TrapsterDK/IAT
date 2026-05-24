import { isEditableTarget } from "./core/utils.mjs";
import type { createSessionFlow } from "./session/flow.mjs";
import { ResponseSide, SessionStateKind, type RuntimeState } from "./state/types.mjs";

export function bindAppController(
  appRoot: HTMLElement,
  document: Document,
  render: () => void,
  runtime: RuntimeState,
  sessionFlow: ReturnType<typeof createSessionFlow>,
) {
  document.addEventListener("keydown", handleKeydown);
  appRoot.addEventListener("click", handleClick);

  function handleClick(event: MouseEvent) {
    const target = event.target;
    if (!(target instanceof Element)) {
      return;
    }

    const actionElement = target.closest<HTMLElement>("[data-action]");
    if (actionElement === null) {
      return;
    }

    switch (actionElement.dataset.action) {
      case "clear-error":
        runtime.ui.screenError = null;
        runtime.catalog.error = null;
        render();
        return;

      case "start-session": {
        const { slug } = actionElement.dataset;
        if (slug !== undefined && slug !== "") {
          void sessionFlow.startSession(slug);
        }
        return;
      }

      case "begin-test":
        void sessionFlow.beginTest();
        return;

      case "respond-left":
        handlePointerResponse(ResponseSide.Left);
        return;

      case "respond-right":
        handlePointerResponse(ResponseSide.Right);
        return;

      case "retry-preload":
        void sessionFlow.preloadSessionImages();
        return;

      case "retry-uploads":
        void sessionFlow.flushQueuedBlockUploads();
        return;

      case "back-to-catalog":
        returnToCatalog();
        return;

      default:
        return;
    }
  }

  function handleKeydown(event: KeyboardEvent) {
    if (isEditableTarget(event.target) || runtime.device.prefersTouchInput || event.repeat) {
      return;
    }

    switch (event.key) {
      case "e":
      case "E":
        handleKeyboardResponse(event, ResponseSide.Left);
        return;

      case "i":
      case "I":
        handleKeyboardResponse(event, ResponseSide.Right);
        return;

      default:
        return;
    }
  }

  function handlePointerResponse(side: ResponseSide) {
    if (!runtime.device.prefersTouchInput) {
      return;
    }

    switch (runtime.session?.state) {
      case SessionStateKind.BlockIntro:
        void sessionFlow.beginCurrentBlock();
        return;

      case SessionStateKind.Trial:
        sessionFlow.registerResponse(side);
        return;

      default:
        return;
    }
  }

  function handleKeyboardResponse(event: KeyboardEvent, side: ResponseSide) {
    const session = runtime.session;
    if (session === null) {
      return;
    }

    switch (session.state) {
      case SessionStateKind.BlockIntro:
        event.preventDefault();
        void sessionFlow.beginCurrentBlock();
        return;

      case SessionStateKind.Trial:
        event.preventDefault();
        sessionFlow.registerResponse(side);
        return;

      default:
        return;
    }
  }

  function returnToCatalog() {
    const session = runtime.session;

    switch (session?.state) {
      case undefined:
      case SessionStateKind.Results:
        break;

      default:
        if (window.confirm("Leave this test and lose the current progress?") !== true) {
          return;
        }
    }

    sessionFlow.clearSession();
    void sessionFlow.fetchCatalog();
  }
}
