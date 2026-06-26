import { createCoreProtocolClientFromJsonlBridge } from "./bridgeClient.js";
import { JsonlMessageRouter } from "./jsonlBridge.js";

export class CoreSessionClient {
  constructor({ sendLine, router, sessionId = "desktop-session" }) {
    this.router = router || new JsonlMessageRouter();
    this.client = createCoreProtocolClientFromJsonlBridge({
      sendLine,
      router: this.router,
    });
    this.sessionId = sessionId;
  }

  onEvent(listener) {
    return this.router.onEvent(listener);
  }

  handleLine(line) {
    return this.router.handleLine(line);
  }

  async attach(metadata = {}) {
    return this.client.desktopAttach(this.sessionId, metadata);
  }

  async detach() {
    return this.client.desktopDetach(this.sessionId);
  }

  async desktopState() {
    return this.client.desktopState();
  }

  async desktopCommand(command, value) {
    return this.client.desktopCommand(command, value, this.sessionId);
  }

  async createConversation(title = "Yue Desktop") {
    return this.client.createConversation(title);
  }

  async sendConversationMessage(conversationId, content, provider) {
    return this.client.sendConversationMessage(conversationId, content, provider);
  }
}
