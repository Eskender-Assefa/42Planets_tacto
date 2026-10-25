import { useCallback, useEffect, useRef, useState } from "react";
import { freshNarration } from "@/lib/briefing";

type Queued = { text: string; createdAt: string };
export function useSpeech(sentences: string[]) {
  const [supported, setSupported] = useState(false);
  const [voices, setVoices] = useState<SpeechSynthesisVoice[]>([]);
  const [voiceId, setVoiceId] = useState("");
  const [rate, setRate] = useState(1);
  const [status, setStatus] = useState<"idle" | "playing" | "paused">("idle");
  const [current, setCurrent] = useState(-1);
  const data = useRef(sentences); data.current = sentences;
  const settings = useRef({ voices, voiceId, rate }); settings.current = { voices, voiceId, rate };
  const index = useRef(-1);
  const generation = useRef(0);
  const queue = useRef<Queued[]>([]);
  const busy = useRef(false);
  const utterance = useRef<SpeechSynthesisUtterance | null>(null);
  const synth = () => typeof window !== "undefined" && "speechSynthesis" in window ? window.speechSynthesis : null;
  const stop = useCallback(() => {
    generation.current++; queue.current = []; busy.current = false; index.current = -1;
    synth()?.cancel(); utterance.current = null; setStatus("idle"); setCurrent(-1);
  }, []);
  useEffect(() => {
    const engine = synth();
    if (!engine || typeof SpeechSynthesisUtterance === "undefined") return;
    setSupported(true);
    const load = () => {
      const available = engine.getVoices(); setVoices(available);
      let saved = ""; try { saved = localStorage.getItem("hollerau-voice") ?? ""; } catch { /* Storage may be disabled. */ }
      const preferred = available.find((v) => v.voiceURI === saved) ?? available.find((v) => /^en/i.test(v.lang) && /Natural|Neural|Google|Online/i.test(v.name)) ?? available.find((v) => /^en-(GB|US)/i.test(v.lang)) ?? available.find((v) => /^en/i.test(v.lang));
      if (preferred) setVoiceId(preferred.voiceURI);
    };
    load(); engine.addEventListener("voiceschanged", load);
    return () => { engine.removeEventListener("voiceschanged", load); generation.current++; queue.current = []; busy.current = false; engine.cancel(); };
  }, []);
  const signature = JSON.stringify(sentences);
  useEffect(() => { stop(); }, [signature, stop]);
  const speak = useCallback((text: string, done: () => void) => {
    const engine = synth(); if (!engine || typeof SpeechSynthesisUtterance === "undefined") return;
    const token = generation.current;
    const u = new SpeechSynthesisUtterance(text);
    const config = settings.current;
    u.voice = config.voices.find((v) => v.voiceURI === config.voiceId) ?? null;
    u.lang = u.voice?.lang ?? "en-GB"; u.rate = config.rate;
    u.onend = () => { if (token === generation.current) done(); };
    u.onerror = () => { if (token === generation.current) { busy.current = false; queue.current = []; setStatus("idle"); setCurrent(-1); } };
    utterance.current = u; engine.speak(u);
  }, []);
  const run = useCallback(function next(at: number) {
    const text = data.current[at];
    if (!text) { busy.current = false; setStatus("idle"); setCurrent(-1); return; }
    busy.current = true; index.current = at; setCurrent(at); setStatus("playing");
    speak(text, () => next(at + 1));
  }, [speak]);
  const play = useCallback((at = 0) => { if (!synth()) return; stop(); synth()?.resume(); run(Math.max(0, at)); }, [stop, run]);
  const drain = useCallback(function next() {
    const item = queue.current.shift();
    if (!item) { busy.current = false; setStatus("idle"); return; }
    if (!freshNarration(item.createdAt)) { next(); return; }
    busy.current = true; setStatus("playing"); speak(item.text, next);
  }, [speak]);
  const enqueue = useCallback((text: string, createdAt: string) => {
    if (!synth() || !text || !freshNarration(createdAt)) return;
    queue.current.push({ text, createdAt }); if (!busy.current) drain();
  }, [drain]);
  const chooseVoice = (id: string) => { setVoiceId(id); try { localStorage.setItem("hollerau-voice", id); } catch { /* Storage may be disabled. */ } };
  return { supported, voices, voiceId, chooseVoice, rate, setRate, status, current, play, stop, enqueue,
    pause: () => { synth()?.pause(); setStatus("paused"); }, resume: () => { synth()?.resume(); setStatus("playing"); },
    previous: () => play(Math.max(0, index.current - 1)), next: () => { if (index.current + 1 >= data.current.length) stop(); else play(index.current + 1); } };
}