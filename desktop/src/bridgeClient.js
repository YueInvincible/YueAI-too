import { CoreProtocolClient } from "./protocol.js";
import { JsonlMessageRouter, createRequestEnvelope } from "./jsonlBridge.js";

export class JsonlBridgeTransport {
  constructor({ sendLine, router }) {
    if (typeof sendLine !== "function") {
      throw new TypeError("sendLine is required");
    }
    this.sendLine = sendLine;
    this.router = router || new JsonlMessageRouter();
  }

  async request({ method, params = {} }) {
    const envelope = createRequestEnvelope(method, params);
    const pending = this.router.createPendingRequest(envelope);
    await this.sendLine(JSON.stringify(envelope));
    return pending;
  }
}

export function createCoreProtocolClientFromJsonlBridge(options) {
  return new CoreProtocolClient(new JsonlBridgeTransport(options));
}
