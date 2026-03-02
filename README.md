# Themeable SQL Clicker

A simple Cookie Clicker-style game with a **working SQL database** (SQLite) and themeable content.

## Features
- Click to gain resources
- Buy upgrades that generate passive resources/sec
- State persisted in `game.db` using SQL tables
- Easy customization via `config/game_config.json`

## Run
```bash
python3 server.py
```
Then open <http://localhost:8000>.

## Customizing theme and upgrades
Edit `config/game_config.json`:
- `theme.title`, `theme.resourceName`, `theme.actionLabel`, colors, emoji
- Add/remove upgrades in `upgrades`

Example ideas:
- Coffee Clicker (`resourceName`: beans)
- Space Miner (`resourceName`: ore)
- Book Publisher (`resourceName`: pages)

After editing config, refresh the app.

## SQL schema
`server.py` creates these tables:
- `game_state(id, resource_count, total_clicks, last_updated)`
- `owned_upgrades(upgrade_id, quantity)`
