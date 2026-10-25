import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useSpeech } from "@/hooks/useSpeech";

afterEach(() => { vi.unstubAllGlobals(); });
function engine() {
  const spoken: { text: string; onend: () => void }[] = [];
  const speech = { getVoices: () => [], addEventListener: vi.fn(), removeEventListener: vi.fn(), speak: vi.fn((u) => spoken.push(u)), cancel: vi.fn(), pause: vi.fn(), resume: vi.fn() };
  vi.stubGlobal("speechSynthesis", speech);
  vi.stubGlobal("SpeechSynthesisUtterance", class { text: string; constructor(text: string) { this.text = text; } });
  return { speech, spoken };
}
describe("Speech playback", () => {
  it("plays, pauses, resumes and advances one sentence at a time", () => {
    const { speech, spoken } = engine(); const { result, unmount } = renderHook(() => useSpeech(["First.", "Second."]));
    act(() => result.current.play()); expect(spoken.map((u) => u.text)).toEqual(["First."]);
    act(() => result.current.pause()); expect(result.current.status).toBe("paused"); expect(speech.pause).toHaveBeenCalled();
    act(() => result.current.resume()); expect(result.current.status).toBe("playing"); expect(speech.resume).toHaveBeenCalled();
    act(() => spoken[0]?.onend()); expect(result.current.current).toBe(1); expect(spoken.map((u) => u.text)).toEqual(["First.", "Second."]);
    unmount(); expect(speech.cancel).toHaveBeenCalled();
  });
  it("speaks just one audit turn and queues live narration without overlap", () => {
    const { spoken } = engine(); const { result } = renderHook(() => useSpeech(["First.", "Second."]));
    act(() => result.current.play(0, true)); act(() => spoken[0]?.onend()); expect(spoken).toHaveLength(1);
    const now = new Date().toISOString();
    act(() => { result.current.enqueue("Live one.", now); result.current.enqueue("Live two.", now); result.current.enqueue("Old.", new Date(Date.now() - 61000).toISOString()); });
    expect(spoken).toHaveLength(2); act(() => spoken[1]?.onend()); expect(spoken).toHaveLength(3); act(() => spoken[2]?.onend()); expect(spoken).toHaveLength(3);
  });
  it("leaves speech unsupported when the browser has no engine", () => {
    vi.stubGlobal("speechSynthesis", undefined);
    const { result } = renderHook(() => useSpeech(["Transcript."]));
    expect(result.current.supported).toBe(false);
    act(() => result.current.play()); expect(result.current.status).toBe("idle");
  });
  it("cancels when the script changes and ignores canceled callbacks", () => {
    const { spoken, speech } = engine();
    const { result, rerender } = renderHook(({ text }) => useSpeech([text]), { initialProps: { text: "Old session." } });
    act(() => result.current.play()); const before = speech.cancel.mock.calls.length;
    rerender({ text: "New session." }); expect(speech.cancel.mock.calls.length).toBeGreaterThan(before);
    act(() => spoken[0]?.onend()); expect(spoken).toHaveLength(1); expect(result.current.status).toBe("idle");
  });
  it("prefers natural English voices and remembers the selected voice", () => {
    const { speech } = engine();
    const available = [{ voiceURI: "plain", name: "English", lang: "en-GB" }, { voiceURI: "natural", name: "Natural English", lang: "en-US" }];
    speech.getVoices = () => available as unknown as ReturnType<typeof speech.getVoices>;
    localStorage.removeItem("hollerau-voice");
    const { result } = renderHook(() => useSpeech(["Sentence."]));
    expect(result.current.voiceId).toBe("natural");
    act(() => result.current.chooseVoice("plain")); expect(localStorage.getItem("hollerau-voice")).toBe("plain");
    localStorage.removeItem("hollerau-voice");
  });
});