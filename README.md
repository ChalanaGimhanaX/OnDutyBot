# On Duty Bot

A Discord bot that gives moderators an on-duty toggle inside a dedicated staff channel. The bot posts a persistent embed with two buttons ("Go On Duty" and "Go Off Duty"). Clicking the buttons adds or removes the configured on-duty role, so the rest of your team knows who is actively moderating.

The bot also watches for pings of moderators who are off duty. If a member without administrator permissions mentions an off-duty moderator, the pinged message is deleted and a warning is posted to the channel.

## Features
- Persistent duty panel embed with Discord buttons using the modern components API.
- Automatic on-duty role management for moderators.
- Prevents non-admin members from pinging moderators who are off duty.
- Environment-driven configuration so no secrets live in the codebase.

## Getting Started
1. Install Python 3.10 or newer.
2. Create and activate a virtual environment (recommended).
3. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy `.env.example` to `.env` and fill in the required IDs and your bot token.
   - `DISCORD_TOKEN`: the bot token from the Discord Developer Portal.
   - `STAFF_CHANNEL_ID`: the channel where the duty panel should live.
   - `ONDUTY_ROLE_ID`: the role granted to moderators who are on duty.
   - `MODERATOR_ROLE_IDS` (optional): comma-separated role IDs that should be treated as moderators when checking mentions.
   - `ALLOWED_TOGGLE_ROLE_IDS` (optional): comma-separated role IDs allowed to press the duty buttons if they lack mod permissions.
5. Invite the bot to your server with the `Manage Roles`, `View Channel`, `Send Messages`, and `Manage Messages` permissions.
6. Run the bot:
   ```bash
   python bot.py
   ```

When the bot starts, it posts (or refreshes) the duty panel in the configured staff channel. Moderators with appropriate permissions can toggle themselves on and off duty from there.

## Notes
- The bot needs the **on-duty role** to sit below its highest role so it can assign and remove it.
- Mentions by administrators are ignored so leadership can override the restriction when needed.
- Duplicate duty panel messages can be deleted manually; the bot will refresh the latest one on startup.
- Update the embed styling inside `bot.py` if you want to match your server theme.
