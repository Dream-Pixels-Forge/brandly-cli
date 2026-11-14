# Subgoals — v0.15.6 Automatic STT / Translation for `brandly voice-match`

**Status:** Frozen design — implemented against this spec  
**Version:** v0.15.6 (minor: one new capability + one CLI option)  
**Base:** brandly-cli 0.15.5  
**Closes:** the last remaining code TODO — `src/brandly_cli/dubbing.py:234`
("transcription/translation not implemented").

**Design authority:** this file. No code without RED→GREEN tests.

---

## Problem

`dub_video()` had no automatic speech-to-text. The only way to dub a video was
to pass an explicit `transcript` argument; without it the function returned
`{"error": "transcript required"}`. That made the `brandly voice-match` CLI
command unusable for its stated purpose — the user must supply a transcript
that the tool is supposed to produce.

## Design

### Backend — faster-whisper, optional and lazy

- **Backend:** `faster-whisper` (CTranslate2 Whisper). Optional dependency,
  exposed as the `stt` extra: `pip install brandly-cli[stt]`.
- **Why optional:** it pulls `ctranslate2` + `av` (hundreds of MB). It must
  never be a core dependency.
- **Import guard:** `try: from faster_whisper import WhisperModel / except
  ImportError` → `FASTER_WHISPER_AVAILABLE = False`. The module imports
  cleanly with or without the backend.
- **Lazy model load:** `_load_whisper_model(model_size="base")` constructs
  `WhisperModel(model_size, device="cpu", compute_type="int8")`. It is loaded
  **per call**, never at import time — importing `brandly_cli.dubbing` must not
  trigger a model download. A construction failure returns `None` (degrade,
  don't raise).

### Transcription — `_transcribe_audio(audio_path, source_lang, target_lang)`

- Returns the transcribed (and optionally translated) text, or `None` on any
  failure.
- **Task selection:** `task="translate"` when `target_lang` differs from
  `source_lang`, else `task="transcribe"`.
- **Language:** passed to Whisper only for `transcribe` (for `translate`,
  Whisper needs the source language detected, so it is left as `None`).
- **VAD:** `vad_filter=True`, `vad_parameters={"min_silence_duration_ms": 500}`
  to skip silence.
- **Blocking call:** run inside `loop.run_in_executor(None, ...)` so the event
  loop is not blocked by inference.
- **Empty result:** whitespace-only output normalises to `None` (a blank
  transcript must never reach the TTS stage).

### Pipeline wiring — `dub_video()`

- `transcript` argument semantics:
  - **`transcript` provided** → used verbatim; the STT backend is never
    invoked.
  - **`transcript` is `None`** → `_transcribe_audio()` runs automatically.
- **Honest failure:** when automatic transcription cannot run or fails, return
  `{"error": ...}` naming both escape hatches (provide `transcript`, or
  install `brandly-cli[stt]`). Never fabricate a transcript.

### CLI — `brandly voice-match --transcript`

- New `--transcript TEXT` option forwarded to `dub_video(transcript=...)`.
- This is the escape hatch the error message names — the CLI must expose it.
- `--transcript` is optional: without it the command now works end-to-end on
  any machine that has the `stt` extra installed.

### Tests (RED→GREEN)

`tests/test_dubbing_transcription.py` (13 tests):
- `_load_whisper_model`: `None` when the backend is unavailable; CPU/int8
  construction; `None` when construction raises.
- `_transcribe_audio`: `None` when unavailable; segments joined; `transcribe`
  task for same-language; `translate` task for cross-language; blank output →
  `None`; a raising backend → `None`.
- `dub_video`: an explicit transcript skips STT entirely; missing transcript
  with no backend → honest error naming `faster-whisper` and `transcript`; the
  auto-transcribed text is what reaches the TTS stage.
- CLI: `--transcript` is accepted and forwarded to `dub_video`.

### Gates

Full suite green, `ruff check src/ tests/` clean, `mypy src/` clean (the only
local mypy findings are the pre-existing `PIL` `import-untyped` ones caused by
the locally-installed Pillow 10.2.0 lacking `py.typed`; CI installs a newer
Pillow and reports "Success: no issues found").

## Explicit non-goals

- **No core dependency** on `faster-whisper` — it stays behind the `stt` extra.
- **No model download at import time** — loading is lazy and per-call.
- **No word-level timing alignment.** The pipeline replaces the whole audio
  track; it does not lip-sync per segment. Out of scope for v0.15.6.
- **No GPU acceleration.** CPU int8 only — the default path must work on any
  machine without CUDA.
