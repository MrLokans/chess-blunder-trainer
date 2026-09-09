## Browser Automation

Use `agent-browser` for web automation. Run `agent-browser --help` for all commands.

Core workflow:
1. `agent-browser open <url>` - Navigate to page
2. `agent-browser snapshot -i` - Get interactive elements with refs (@e1, @e2)
3. `agent-browser click @e1` / `fill @e2 "text"` - Interact using refs
4. Re-snapshot after page changes

When taking screenshots of web apps, always use 2x (Retina) resolution/device scale factor. Never use 1x CSS scale for screenshots intended for documentation or landing pages. For the repeatable LLM UI-review workflow, see [UI Screenshot Capture](docs/screenshot-prompt.md).

## Capture the overviews

1. Start the app and load analyzed games if dashboard data matters.
2. Run:

   ```bash
   ./scripts/capture-screenshots.sh
   ```

3. Attach the PNGs from the printed `screenshots/<datetime>/` directory to the LLM.

The script uses a 1440×1080 desktop viewport at 2x Retina scale, producing 2880×2160 PNGs. Each run creates these gitignored files:

```text
page-profile.png     page-dashboard.png  page-traps.png    page-starred.png
page-profiles.png    page-management.png page-import.png   page-settings.png
```

Pass another running app URL if needed:

```bash
./scripts/capture-screenshots.sh http://localhost:8001
```

## Review content below the fold

Do not send a generic full-page image. Navigate the live page to the relevant section, then have the agent capture that viewport or element separately. This keeps text and controls legible to vision models.
