declare module "@daily-co/daily-js" {
  interface DailyCallFrame {
    join(options: { url: string; token?: string }): Promise<void>;
    leave(): Promise<void>;
    destroy(): void;
    setLocalAudio(enabled: boolean): void;
    setLocalVideo(enabled: boolean): void;
  }

  interface DailyFrameOptions {
    iframeStyle?: Record<string, string>;
    showLeaveButton?: boolean;
    showFullscreenButton?: boolean;
  }

  const DailyIframe: {
    createFrame(container: HTMLElement, options?: DailyFrameOptions): DailyCallFrame;
  };

  export default DailyIframe;
}
