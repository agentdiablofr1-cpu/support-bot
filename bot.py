import discord
from discord.ext import commands
from discord import ui, SelectOption
import re
import requests
import asyncio

# ==================================================
# CONFIG
# ==================================================
SUPPORT_GUILD_ID = 1459970864236986562
BOT_NAME = "Support No Limit RP"
TOKEN = "MTQ2MDM1ODE0MzI5MTY5MTAxOA.GLieRh.KkFolPvtbi-MWank0H9iEKL8ikxiIXqTWXrZGk"


GLOBAL_ROLE_NAME = "Responsable"

OWNER_IDS = [
    775169308434759700,
    1266464826289557599,
    735926063464710305,
    530097139557335071,
    979299048819417088,
]

TICKET_CATEGORIES = {
    "Autres / Question": 1460361148867281049,
    "Reprise d'entreprise": 1461091449071206503,
    "Reprise d'organisation": 1461091651069022329,
    "Ticket Deban": 1461091845504368793,
    "Plainte Staff": 1461091955948785704,
    "Plainte Joueur": 1461092106322841712,
    "Ticket Fondateur": 1480185638585237645,
}

CATEGORY_ROLES = {
    "Autres / Question": "Staff",
    "Reprise d'entreprise": "Resp Légal",
    "Reprise d'organisation": "Resp Illégal",
    "Ticket Deban": "Modérateur",
    "Plainte Staff": "Resp Staff",
    "Plainte Joueur": "Staff",
    "Ticket Fondateur": "Fondateur",
}

CATEGORY_EMOJIS = {
    "Autres / Question": "❓",
    "Reprise d'entreprise": "🏢",
    "Reprise d'organisation": "💀",
    "Ticket Deban": "🚫",
    "Plainte Staff": "⚠️",
    "Plainte Joueur": "👤",
    "Ticket Fondateur": "👑",
}

# ==================================================
# BOT
# ==================================================
intents = discord.Intents.all()
bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    owner_ids=set(OWNER_IDS)
)
active_tickets = {}


# ==================================================
# CLOSE TICKET
# ==================================================
class CloseTicketView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="🔒 Fermer le ticket", style=discord.ButtonStyle.danger)
    async def close_button(self, interaction, button):
        for uid, info in active_tickets.items():
            if info["channel_id"] == interaction.channel.id:
                user = bot.get_user(uid)

                roles = [r for r in interaction.user.roles if r.name != "@everyone"]
                grade = roles[-1].name if roles else "Support"

                if user:
                    embed = discord.Embed(
                        title=f"Ticket #{info['ticket_number']}",
                        description=(
                            f"**{BOT_NAME}**\n"
                            f"Ticket fermé avec succès.\n"
                            f"`{grade} - {interaction.user.display_name}` a fermé le ticket."
                        ),
                        color=0x00FFFF
                    )
                    await user.send(embed=embed)

                del active_tickets[uid]
                await interaction.channel.delete()
                return

        await interaction.response.send_message("❌ Ticket invalide.", ephemeral=True)

# ==================================================
# READY
# ==================================================
@bot.event
async def on_ready():
    print(f"{bot.user} prêt")

# ==================================================
# MESSAGES / TICKETS
# ==================================================
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if isinstance(message.channel, discord.DMChannel):
        user_id = message.author.id

        if user_id in active_tickets:
            channel = bot.get_channel(active_tickets[user_id]["channel_id"])
            if channel:
                await channel.send(f"**{message.author.display_name}**: {message.content}")
            return

        embed = discord.Embed(
            title="Support No Limit RP",
            description="Merci de sélectionner la catégorie de votre demande.",
            color=0x00FFFF
        )

        class CategorySelect(ui.View):
            def __init__(self, user_message):
                super().__init__(timeout=180)
                self.user_message = user_message

            @ui.select(
                placeholder="Choisissez une catégorie",
                min_values=1,
                max_values=1,
                options=[
                    SelectOption(label=cat, value=cat, emoji=CATEGORY_EMOJIS.get(cat))
                    for cat in TICKET_CATEGORIES
                ]
            )
            async def callback(self, interaction, select):
                selected = select.values[0]
                guild = bot.get_guild(SUPPORT_GUILD_ID)
                category = guild.get_channel(TICKET_CATEGORIES[selected])

                existing = [ch for ch in category.text_channels if re.search(r"\d+", ch.name)]
                number = max(
                    [int(re.search(r"\d+", ch.name).group()) for ch in existing],
                    default=0
                ) + 1

                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                    interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                }

                role = discord.utils.get(guild.roles, name=CATEGORY_ROLES.get(selected))
                if role:
                    overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

                channel = await guild.create_text_channel(
                    f"{selected.lower().replace(' ', '-')}-{number}",
                    category=category,
                    overwrites=overwrites
                )

                active_tickets[user_id] = {
                    "channel_id": channel.id,
                    "ticket_number": number,
                    "category": selected
                }

                await interaction.user.send(
                    embed=discord.Embed(
                        title=f"Ticket #{number}",
                        description=(
                            f"**{BOT_NAME}**\n"
                            f"Votre ticket a été créé avec succès.\n"
                            f"Catégorie : **{selected}**"
                        ),
                        color=0x00FFFF
                    )
                )

                await channel.send(f"**{interaction.user.display_name}**: {self.user_message.content}")
                await channel.send("🔧 Gestion du ticket", view=CloseTicketView())

        await message.channel.send(embed=embed, view=CategorySelect(message))

    elif any(info["channel_id"] == message.channel.id for info in active_tickets.values()):
        if message.reference:
            return
        if message.content.startswith("!") or not message.content.strip():
            return

        user_id = next(uid for uid, info in active_tickets.items() if info["channel_id"] == message.channel.id)
        user = bot.get_user(user_id)

        if user:
            roles = [r for r in message.author.roles if r.name != "@everyone"]
            grade = roles[-1].name if roles else "Support"
            await user.send(f"`{grade} - {message.author.display_name}`: {message.content}")

    await bot.process_commands(message)
    
# ==================================================
# GLOBAL ROLE
# ==================================================
@bot.command()
@commands.is_owner()
async def globalrole(ctx, member: discord.Member):
    added = 0

    for guild in bot.guilds:
        role = discord.utils.get(guild.roles, name=GLOBAL_ROLE_NAME)

        if role:
            target = guild.get_member(member.id)

            if target:
                try:
                    await target.add_roles(role)
                    added += 1
                except:
                    pass

    await ctx.send(f"✅ Rôle ajouté sur {added} serveur(s).")


@bot.command()
@commands.is_owner()
async def unglobalrole(ctx, member: discord.Member):
    removed = 0

    for guild in bot.guilds:
        role = discord.utils.get(guild.roles, name=GLOBAL_ROLE_NAME)

        if role:
            target = guild.get_member(member.id)

            if target:
                try:
                    await target.remove_roles(role)
                    removed += 1
                except:
                    pass

    await ctx.send(f"✅ Rôle retiré sur {removed} serveur(s).")

# ==================================================
# RUN
# ==================================================
bot.run(TOKEN)