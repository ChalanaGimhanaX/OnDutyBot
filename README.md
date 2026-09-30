# OnDutyBot — Discord Moderator Duty Management

A Python Discord bot that lets moderators toggle their on-duty status through persistent buttons and a shared staff panel.

**Stack:** Python · discord.py · python-dotenv

## Features

- Go On Duty / Go Off Duty buttons add or remove a configured role.
- A persistent panel lists members currently on duty.
- Configurable roles determine who may use the duty controls.
- Off-duty moderator mentions trigger an attempt to delete the message and post a temporary warning.
- Environment variables configure the bot and community-specific roles.

## Setup

Use Python 3.10+ and a Discord application with a bot.

```bash
git clone https://github.com/ChalanaGimhanaX/OnDutyBot.git
cd OnDutyBot
python -m venv .venv
```

Activate `.venv\Scripts\Activate.ps1` in PowerShell or `source .venv/bin/activate` on macOS/Linux, then:

```bash
python -m pip install -r requirements.txt
```

Copy `.env.example` to `.env` and supply your own values:

| Variable | Purpose |
| --- | --- |
| `DISCORD_TOKEN` | Bot token; keep private |
| `STAFF_CHANNEL_ID` | Channel where the duty panel appears |
| `ONDUTY_ROLE_ID` | Role granted to moderators on duty |
| `MODERATOR_ROLE_IDS` | Optional comma-separated moderator role IDs |
| `ALLOWED_TOGGLE_ROLE_IDS` | Optional comma-separated roles allowed to toggle duty |

Enable Server Members and Message Content privileged intents in the Discord Developer Portal. Invite the bot with View Channel, Read Message History, Send Messages, Embed Links, Manage Roles, and Manage Messages permissions. Place its highest role above the on-duty role.

```bash
python bot.py
```

## How it works

`bot.py` registers a persistent `discord.ui.View`, locates or creates the panel, and handles role changes through Discord interactions. Message events check mentions against moderator roles and duty status.

## Manual verification

In a test server, check that an allowed moderator can toggle duty, an unauthorized member cannot toggle, and the panel updates after a successful role change. Also test missing-permission and role-hierarchy behavior.

The mention handler does not explicitly exempt administrators. Adapt and test this policy before enabling message deletion in a live community.

## Code guide

- `bot.py`: duty panel, role permissions, and message handling.
- `.env.example`: placeholder configuration.
- `requirements.txt`: Python dependencies.

Keep bot tokens, local configuration, bytecode, and runtime logs outside version control.

## Author

[Chalana Gimhana](https://github.com/ChalanaGimhanaX)
