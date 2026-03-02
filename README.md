# Themeable Clicker (No Database)

This version is fully frontend-based and **does not use SQL/database**.
Your progress is saved in the browser with `localStorage`.

## Run
From project root:

```bash
python3 -m http.server 8000
```

Then open <http://localhost:8000/templates/>.

## How saving works
- Save key: `themeable_clicker_save_v2`
- Data stored: resources, clicks, owned upgrades, last update timestamp
- Works across refreshes and browser restarts (same browser profile)

## Customize theme and subject
Edit `config/game_config.json`:
- Change labels (`title`, `resourceName`, `actionLabel`)
- Change emoji/colors (`emoji`, `background`, `primary`, `accent`)
- Change/add upgrades in `upgrades` (`name`, `description`, `base_cost`, `cps`)

You can turn this into anything (coffee, mining, books, etc.) without code changes.
