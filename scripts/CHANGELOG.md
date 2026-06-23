# Render GUI Changelog

| Version | Date | Changes | Status |
|---------|------|---------|--------|
| v0.1 | 2026-06-22 | render script + bat launcher (viewport screenshot, `--no-window`) | Working |
| v0.2 | 2026-06-22 | PySide6 GUI (resolution, SPP, per-variant exposure, log panel) | Working |
| v0.3 | 2026-06-22 | Exposure via carb `cameraShutter` | Broken (white images) |
| v0.4 | 2026-06-23 | Exposure via USD `exposure` (EV) | Reverted |
| v0.5 | 2026-06-23 | Exposure via USD `exposure:time` | Working |
| v0.6 | 2026-06-23 | Resolution debug logging added | Done |
| v0.7 | 2026-06-23 | Fix resolution: render scale 100% + fill_frame off | Working (1024) |
| v0.8 | 2026-06-23 | Fix 4096 black: longer post-switch wait + double reset | Partial (3-7 identical) |
| v0.9 | 2026-06-23 | Per-variant Kit restart (removed: GPU can't do >2048 anyway) | Reverted |
| v0.10 | 2026-06-23 | Fix SPP: set totalSpp from GUI; log render settings; USD/output path browse | Buffer bleed |
| v0.11 | 2026-06-23 | Fix buffer bleed: 60-frame Hydra sync before reset; single clean reset | Still shifted |
| v0.12 | 2026-06-23 | Await capture completion: wait_async_capture() + file size logging | Still 0KB |
| v0.13 | 2026-06-23 | Poll until file on disk; delete before capture; log frame count | 4096 timeout |
| v0.14 | 2026-06-23 | Scale poll limit by resolution (4096→3355 frames) | 4096 unreliable (GPU VRAM) |
| v0.15 | 2026-06-23 | GUI: SPI + Specular Bounces controls; metadata.json output (from Kit runtime + USD) | Frame offset |
| v0.16 | 2026-06-23 | Diagnostic: per-step logging, pre-capture drain, render_log.txt in output | Readback buffer reuse |
| v0.17 | 2026-06-23 | Fix tearing: time-based file poll (120s timeout), must complete before next variant | Current |

**4096 결론**: RTX 4060 (8GB)으로 4096×4096 path tracing은 VRAM 부족으로 안정적 렌더링 불가.
2048×2048이 이 GPU의 실용적 최대 해상도. 4096 필요 시 RTX 4090 (24GB) 이상 권장.
