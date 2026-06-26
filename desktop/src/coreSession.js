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

  async providersHealth() {
    return this.client.providersHealth();
  }

  async getConversationSettings() {
    return this.client.getConversationSettings();
  }

  async updateConversationSettings(payload) {
    return this.client.updateConversationSettings(payload);
  }

  async getOpenAICompatibleSettings() {
    return this.client.getOpenAICompatibleSettings();
  }

  async updateOpenAICompatibleSettings(payload) {
    return this.client.updateOpenAICompatibleSettings(payload);
  }

  async getAnthropicMessagesSettings() {
    return this.client.getAnthropicMessagesSettings();
  }

  async updateAnthropicMessagesSettings(payload) {
    return this.client.updateAnthropicMessagesSettings(payload);
  }

  async desktopCommand(command, value) {
    return this.client.desktopCommand(command, value, this.sessionId);
  }

  async requestApproval(actionDescription, riskLevel, actor = "desktop-ui") {
    return this.client.requestApproval(
      actionDescription,
      riskLevel,
      actor,
      this.sessionId,
    );
  }

  async listPendingApprovals() {
    return this.client.listPendingApprovals();
  }

  async respondApproval(approvalId, approved) {
    return this.client.respondApproval(approvalId, approved);
  }

  async createConversation(title = "Yue Desktop") {
    return this.client.createConversation(title);
  }

  async sendConversationMessage(conversationId, content, provider) {
    return this.client.sendConversationMessage(conversationId, content, provider);
  }
}
