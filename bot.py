import logging
import os
from typing import Iterable, List

import discord
from discord.ext import commands
from dotenv import load_dotenv

EMBED_TITLE = "Moderator Duty Panel"
log = logging.getLogger("onduty.bot")


def _parse_required_int(name: str) -> int:
    raw_value = os.getenv(name)
    if not raw_value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    try:
        return int(raw_value)
    except ValueError as exc:
        raise RuntimeError(f"Environment variable {name} must be an integer") from exc


def _parse_id_list(name: str) -> List[int]:
    raw_value = os.getenv(name, "")
    values: List[int] = []
    for item in raw_value.split(","):
        stripped = item.strip()
        if not stripped:
            continue
        try:
            values.append(int(stripped))
        except ValueError as exc:
            raise RuntimeError(f"Environment variable {name} must contain integers separated by commas") from exc
    return values


class DutyToggleView(discord.ui.View):
    def __init__(self, bot: "DutyBot") -> None:
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Go On Duty", style=discord.ButtonStyle.success, custom_id="duty:on")
    async def go_on_duty(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self.bot.toggle_duty(interaction, go_on_duty=True)

    @discord.ui.button(label="Go Off Duty", style=discord.ButtonStyle.danger, custom_id="duty:off")
    async def go_off_duty(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self.bot.toggle_duty(interaction, go_on_duty=False)


class DutyBot(commands.Bot):
    def __init__(
        self,
        *,
        staff_channel_id: int,
        on_duty_role_id: int,
        moderator_role_ids: Iterable[int],
        allowed_toggle_role_ids: Iterable[int],
    ) -> None:
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(command_prefix=commands.when_mentioned_or("!"), intents=intents)
        self.staff_channel_id = staff_channel_id
        self.on_duty_role_id = on_duty_role_id
        self.moderator_role_ids = list(moderator_role_ids)
        self.allowed_toggle_role_ids = list(allowed_toggle_role_ids)

    async def setup_hook(self) -> None:
        self.add_view(DutyToggleView(self))

    async def on_ready(self) -> None:
        log.info("Connected as %s (%s)", self.user, getattr(self.user, "id", "unknown"))
        try:
            await self.ensure_duty_panel()
        except Exception:
            log.exception("Failed to ensure duty panel message is present")

    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or not message.guild:
            return
        await self.handle_off_duty_mentions(message)
        await super().on_message(message)

    async def handle_off_duty_mentions(self, message: discord.Message) -> None:
        if not message.mentions:
            return
        duty_role = self.get_on_duty_role(message.guild)
        if duty_role is None:
            log.warning("Could not find on-duty role")
            return
        
        log.info(f"Checking mentions in message from {message.author.display_name}")
        for mentioned in message.mentions:
            log.info(f"Checking mentioned user: {mentioned.display_name}")
            if mentioned.bot or mentioned == message.author:
                log.info(f"Skipping {mentioned.display_name} - bot or self-mention")
                continue
            if not self.is_moderator(mentioned):
                log.info(f"Skipping {mentioned.display_name} - not a moderator")
                continue
            if duty_role in mentioned.roles:
                log.info(f"Skipping {mentioned.display_name} - already on duty")
                continue
            
            log.info(f"Deleting message mentioning off-duty moderator: {mentioned.display_name}")
            try:
                await message.delete()
            except discord.Forbidden:
                log.warning("Missing permission to delete message in #%s", message.channel)
            except discord.NotFound:
                return
            warning = f"{message.author.mention}, {mentioned.display_name} is not currently on duty."
            try:
                await message.channel.send(warning, delete_after=10)
            except discord.Forbidden:
                log.warning("Missing permission to send warning message in #%s", message.channel)
            break

    async def ensure_duty_panel(self) -> None:
        channel = self.get_channel(self.staff_channel_id)
        if channel is None:
            channel = await self.fetch_channel(self.staff_channel_id)
        if not isinstance(channel, discord.TextChannel):
            raise RuntimeError("STAFF_CHANNEL_ID must point to a text channel")
        async for existing in channel.history(limit=50):
            if existing.author == self.user and existing.embeds and existing.embeds[0].title == EMBED_TITLE:
                await existing.edit(embed=self.build_duty_embed(channel.guild), view=DutyToggleView(self))
                log.info("Updated existing duty panel message: %s", existing.id)
                break
        else:
            sent = await channel.send(embed=self.build_duty_embed(channel.guild), view=DutyToggleView(self))
            log.info("Posted new duty panel message: %s", sent.id)

    def get_on_duty_role(self, guild: discord.Guild) -> discord.Role | None:
        return guild.get_role(self.on_duty_role_id)

    def can_toggle_duty(self, member: discord.Member) -> bool:
        if member.guild_permissions.administrator:
            return True
        if member.guild_permissions.manage_guild or member.guild_permissions.manage_messages:
            return True
        return any(role.id in self.allowed_toggle_role_ids for role in member.roles)

    def is_moderator(self, member: discord.Member) -> bool:
        # Check permissions first (admins, mods with kick/ban/manage messages)
        perms = member.guild_permissions
        if perms.administrator or perms.manage_messages or perms.kick_members or perms.ban_members:
            return True
        # Also check specific moderator role IDs if configured
        if self.moderator_role_ids:
            return any(role.id in self.moderator_role_ids for role in member.roles)
        return False

    def build_duty_embed(self, guild: discord.Guild) -> discord.Embed:
        role = self.get_on_duty_role(guild)
        embed = discord.Embed(title=EMBED_TITLE, color=discord.Color.blurple())
        if role is None:
            embed.description = (
                "I could not find the configured on-duty role. Update ONDUTY_ROLE_ID in your .env file "
                "and restart the bot."
            )
            embed.add_field(name="Currently On Duty", value="Unavailable", inline=False)
            return embed
        members = sorted(role.members, key=lambda member: member.display_name.lower())
        if members:
            on_duty_lines = "\n".join(f"- {member.display_name}" for member in members)
        else:
            on_duty_lines = "Nobody is on duty right now."
        embed.description = (
            "Use the buttons below to let the team know when you start or finish a shift."
            "\nModerators with the right permissions can toggle their status at any time."
        )
        embed.add_field(name="On-duty Role", value=role.mention, inline=False)
        embed.add_field(name="Currently On Duty", value=on_duty_lines, inline=False)
        embed.set_footer(text="Remember to hand off when you take a break.")
        return embed

    async def toggle_duty(self, interaction: discord.Interaction, *, go_on_duty: bool) -> None:
        if not interaction.guild:
            await interaction.response.send_message("This can only be used inside a server.", ephemeral=True)
            return
        member = interaction.guild.get_member(interaction.user.id)
        if member is None:
            await interaction.response.send_message("Something went wrong resolving your member profile.", ephemeral=True)
            return
        if not self.can_toggle_duty(member):
            await interaction.response.send_message("You do not have permission to toggle duty status.", ephemeral=True)
            return
        role = self.get_on_duty_role(member.guild)
        if role is None:
            await interaction.response.send_message("The on-duty role is missing. Ask an admin to fix ONDUTY_ROLE_ID.", ephemeral=True)
            return
        already_on_duty = role in member.roles
        if go_on_duty and already_on_duty:
            await interaction.response.send_message("You are already marked as on duty.", ephemeral=True)
            return
        if not go_on_duty and not already_on_duty:
            await interaction.response.send_message("You are already marked as off duty.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        try:
            if go_on_duty:
                await member.add_roles(role, reason="Moderator marked on duty via duty panel")
                confirmation = f"{role.name} role added. You are now on duty."
            else:
                await member.remove_roles(role, reason="Moderator marked off duty via duty panel")
                confirmation = f"{role.name} role removed. You are now off duty."
        except discord.Forbidden:
            await interaction.followup.send(
                "I do not have permission to manage the on-duty role. Check my role hierarchy.",
                ephemeral=True,
            )
            return
        except discord.HTTPException:
            await interaction.followup.send("Failed to update your role due to an API error. Try again.", ephemeral=True)
            return
        try:
            await interaction.message.edit(embed=self.build_duty_embed(member.guild), view=DutyToggleView(self))
        except discord.HTTPException:
            log.exception("Failed to refresh the duty panel embed")
        await interaction.followup.send(confirmation, ephemeral=True)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    load_dotenv()
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_TOKEN is not set in the environment")
    staff_channel_id = _parse_required_int("STAFF_CHANNEL_ID")
    on_duty_role_id = _parse_required_int("ONDUTY_ROLE_ID")
    moderator_role_ids = _parse_id_list("MODERATOR_ROLE_IDS")
    allowed_toggle_role_ids = _parse_id_list("ALLOWED_TOGGLE_ROLE_IDS")
    bot = DutyBot(
        staff_channel_id=staff_channel_id,
        on_duty_role_id=on_duty_role_id,
        moderator_role_ids=moderator_role_ids,
        allowed_toggle_role_ids=allowed_toggle_role_ids,
    )
    bot.run(token)


if __name__ == "__main__":
    main()
