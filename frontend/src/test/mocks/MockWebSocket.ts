export class MockWebSocket {
  static instance: MockWebSocket;
  onmessage: ((e: MessageEvent) => void) | null = null;
  close = vi.fn();
  public url: string;

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instance = this;
  }

  simulateMessage(data: unknown) {
    this.onmessage?.({ data: JSON.stringify(data) } as MessageEvent);
  }
}
