# UI Screenshot Capture

Use this workflow to give an LLM a consistent desktop overview of the app. It captures the initial viewport only: a full-page image becomes too tall for reliable vision-model analysis.

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
