import { Pause, Play, SkipBack, SkipForward, Square } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useSpeech } from "@/hooks/useSpeech";

export function SpeechControls({ speech, large = false }: { speech: ReturnType<typeof useSpeech>; large?: boolean }) {
  if (!speech.supported) return <p className="text-sm text-muted-foreground">This browser has no built-in voice</p>;
  const { status } = speech;
  const action = status === "playing" ? speech.pause : status === "paused" ? speech.resume : () => speech.play();
  const label = status === "playing" ? "Pause" : status === "paused" ? "Resume" : "Play";
  return <div className="space-y-4">
    {large && <Button aria-label={label} title={label} onClick={action} className="mx-auto flex h-32 w-32 rounded-full">{status === "playing" ? <Pause className="size-9" /> : <Play className="size-9" />}</Button>}
    <div className="flex flex-wrap items-center justify-center gap-2">
      <Button size="icon" variant="outline" aria-label="Previous sentence" title="Previous sentence" onClick={speech.previous}><SkipBack /></Button>
      {!large && <Button size="icon" aria-label={label} title={label} onClick={action}>{status === "playing" ? <Pause /> : <Play />}</Button>}
      <Button size="icon" variant="outline" aria-label="Stop" title="Stop" onClick={speech.stop}><Square /></Button>
      <Button size="icon" variant="outline" aria-label="Next sentence" title="Next sentence" onClick={speech.next}><SkipForward /></Button>
      <select aria-label="Speech speed" value={speech.rate} onChange={(e) => speech.setRate(Number(e.target.value))} className="h-9 rounded border border-border bg-background px-2 text-sm">{[0.8, 1, 1.2].map((r) => <option key={r} value={r}>{r}x</option>)}</select>
      <select aria-label="Voice" value={speech.voiceId} onChange={(e) => speech.chooseVoice(e.target.value)} className="h-9 max-w-full rounded border border-border bg-background px-2 text-sm sm:max-w-64"><option value="">System English voice</option>{speech.voices.map((v) => <option key={v.voiceURI} value={v.voiceURI}>{v.name} · {v.lang}</option>)}</select>
    </div>
  </div>;
}