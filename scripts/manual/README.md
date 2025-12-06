# Manual/Interactive Test Scripts

These scripts require human interaction and cannot be run in automated pipelines.

## Scripts

### `interactive-playback-test.py`

Interactive menu-driven testing tool for playback controls.

```bash
python scripts/manual/interactive-playback-test.py 192.168.1.115
```

Features:
- Menu-driven interface
- Manual control of play/pause/stop/resume
- Next/previous track controls
- Shuffle and repeat mode controls
- Real-time status display

Press Ctrl+C or enter 'q' to quit.

### `test-shuffle-repeat-by-source.py`

Comprehensive interactive testing across multiple sources and content types.

```bash
python scripts/manual/test-shuffle-repeat-by-source.py 192.168.1.115
```

Workflow:
1. Start the script
2. Use WiiM app to play content from a source
3. Return to script and press `[t]` to test current source
4. Describe what's playing (e.g., "Spotify Album - Rumors")
5. Script tests shuffle/repeat and records results
6. Repeat for different sources and content types
7. Press `[q]` to save results and see summary

Results saved to `scripts/manual/results/` (gitignored).

## When to Use

Use these scripts when you need to:
- Test behavior across multiple sources manually
- Debug specific playback control issues
- Verify behavior that requires human observation
- Test scenarios that can't be automated

