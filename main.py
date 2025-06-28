import discord
from discord.ext import commands
from discord import app_commands
import os
import asyncio
import random
from keep_alive import keep_alive

# === INTENTS & BOT SETUP ===
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# === CHANNEL IDs ===
GAME_CHANNEL_ID = 1382258120176435241
NORMAL_GAME_ROLE_ID = 1382264485372231700
ANNOUNCEMENT_CHANNEL_ID = 1382253075028512841
MINI_ANNOUNCEMENT_CHANNEL_ID = 1386272071037751356
SNEAK_CHANNEL_ID = 1386272878735003709
TWEET_CHANNEL_ID = 1387567999111794799
OFFICIAL_LINKS_ID = 1382255441215488092

# === XP/LEVEL SYSTEM ===
xp_data = {}
level_curve = lambda lvl: 50 * lvl * 1.5

async def add_xp(user_id, amount):
    user = xp_data.get(user_id, {"xp": 0, "level": 0})
    user["xp"] += amount
    while user["xp"] >= level_curve(user["level"] + 1):
        user["level"] += 1
    xp_data[user_id] = user

@bot.event
async def on_message(message):
    if message.author.bot or message.guild is None:
        return
    await add_xp(message.author.id, random.randint(15, 40))
    await bot.process_commands(message)

# === SLASH COMMANDS ===

@tree.command(name="game", description="Start a Rumble Royale")
@app_commands.describe(
    era="Pick an era",
    type="Choose game type",
    countdown="How many minutes before the fight starts?"
)
@app_commands.choices(
    era=[app_commands.Choice(name=e, value=e) for e in [
        "War", "Aquatic", "Jurassic", "Egyptian", "Zombie", "Pirate",
        "Samurai", "Futuristic", "Modern", "Classic", "Random"
    ]],
    type=[
        app_commands.Choice(name="Normal", value="normal"),
        app_commands.Choice(name="Staff", value="staff")
    ],
    countdown=[
        app_commands.Choice(name="2 minutes", value=2),
        app_commands.Choice(name="3 minutes", value=3),
        app_commands.Choice(name="5 minutes", value=5)
    ]
)
async def game(interaction: discord.Interaction, era: app_commands.Choice[str], type: app_commands.Choice[str], countdown: app_commands.Choice[int]):
    global rumble_active
    if interaction.channel.id != GAME_CHANNEL_ID:
        await interaction.response.send_message("❌ Use this command in the GAME channel.", ephemeral=True)
        return

    if rumble_active:
        await interaction.response.send_message("⚠️ A Rumble is already running.", ephemeral=True)
        return

    if type.value == "normal" and NORMAL_GAME_ROLE_ID not in [role.id for role in interaction.user.roles]:
        await interaction.response.send_message("🚫 You need the game role to start this.", ephemeral=True)
        return

    rumble_active = True
    total_secs = countdown.value * 60
    prize = random.randint(400, 1000)

    await interaction.response.send_message("✅ Rumble countdown started!", ephemeral=True)
    await interaction.channel.send(f"@everyone")
    start_embed = discord.Embed(
        title="💀 Masked Royale RUMBLE BEGINS!",
        description=f"React with 🎭 to join!\n**{countdown.value} minutes** until chaos begins.",
        color=0x000000
    )
    start_embed.set_footer(text=f"ERA: {era.value}")
    msg = await interaction.channel.send(embed=start_embed)
    await msg.add_reaction("🎭")

    for secs in [150, 100, 35]:
        if total_secs > secs:
            await asyncio.sleep(total_secs - secs)
            await interaction.channel.send(f"⏳ `{secs}` seconds left to join...")

    await asyncio.sleep(35)

    msg = await interaction.channel.fetch_message(msg.id)
    users = []
    for r in msg.reactions:
        if str(r.emoji) == "🎭":
            async for user in r.users():
                if not user.bot:
                    users.append(user)

    if len(users) < 2:
        await interaction.channel.send("😴 Not enough warriors. RUMBLE cancelled.")
        rumble_active = False
        return

    participants_text = "\n".join(f"{u.mention}" for u in users)
    await interaction.channel.send(f"@everyone")
    join_embed = discord.Embed(
        title="🌀 Masked Royale Session Started",
        description=f"**Participants:**\n{participants_text}",
        color=0x000000
    )
    join_embed.add_field(name="Era", value=f"🗡 {era.value}", inline=True)
    join_embed.add_field(name="Prize", value=f"💰 {prize}", inline=True)
    join_embed.add_field(name="Gold Per Kill", value=f"🪙 {random.randint(5, 12)}", inline=True)
    await interaction.channel.send(embed=join_embed)
    await asyncio.sleep(2)

    round_num = 1
    eliminated_users = []

    while len(users) > 1:
        await asyncio.sleep(2)
        round_embed = discord.Embed(
            title=f"⚔️ Round {round_num}",
            description="The shadows move...",
            color=0x000000
        )

        kill_count = 1 if len(users) <= 4 else random.randint(1, 2)
        eliminated = random.sample(users, min(kill_count, len(users) - 1))

        for dead in eliminated:
            users.remove(dead)
            eliminated_users.append(dead)
            story = random.choice([
                f"~~{dead.display_name}~~ wandered too deep and was lost.",
                f"~~{dead.display_name}~~ cracked under pressure.",
                f"~~{dead.display_name}~~ got erased by corrupted code.",
                f"~~{dead.display_name}~~ challenged fate and fell.",
                f"~~{dead.display_name}~~ vanished into silence.",
            ])
            round_embed.add_field(name="☠️ Eliminated", value=story, inline=False)
            await asyncio.sleep(2)

        round_embed.set_footer(text=f"Players Left: {len(users)} • Era: {era.value}")
        await interaction.channel.send(embed=round_embed)
        round_num += 1

    await asyncio.sleep(2)
    winner = users[0]
    runners_up = eliminated_users[-2:] if len(eliminated_users) >= 2 else eliminated_users
    await interaction.channel.send(f"🏆 **{winner.mention}** is the LAST MASK STANDING!")

    win_embed = discord.Embed(
        title="👑 WINNER!",
        description=f"Has conquered the Royale.",
        color=0x000000
    )
    win_embed.add_field(name="Reward", value=f"💰 {prize}", inline=True)
    win_embed.set_footer(text=f"Total Players: {len(eliminated_users) + 1}")
    await interaction.channel.send(embed=win_embed)

    if runners_up:
        runners_embed = discord.Embed(
            title="🎖 Runners-Up",
            description="\n".join(f"{u.display_name}" for u in runners_up),
            color=0x000000
        )
        await interaction.channel.send(embed=runners_embed)

    rumble_active = False

# === RANK COMMAND ===
@tree.command(name="rank", description="Check your XP and level.")
async def rank(interaction: discord.Interaction):
    user = xp_data.get(interaction.user.id, {"xp": 0, "level": 0})
    embed = discord.Embed(
        title="📊 Your Rank",
        description=f"**Level:** {user['level']}\n**XP:** {user['xp']:.0f}",
        color=0x000000
    )
    await interaction.response.send_message(embed=embed)

# === LEADERBOARD COMMAND ===
@tree.command(name="leaderboard", description="View top users by level.")
async def leaderboard(interaction: discord.Interaction):
    if not xp_data:
        await interaction.response.send_message("Leaderboard is empty!", ephemeral=True)
        return
    top = sorted(xp_data.items(), key=lambda x: (x[1]["level"], x[1]["xp"]), reverse=True)[:10]
    desc = ""
    for i, (uid, data) in enumerate(top, 1):
        user = await bot.fetch_user(uid)
        desc += f"{i}. **{user.display_name}** - Level {data['level']} | {int(data['xp'])} XP\n"
    embed = discord.Embed(title="🏆 Leaderboard", description=desc, color=0x000000)
    await interaction.response.send_message(embed=embed)

# === ANNOUNCEMENT COMMAND ===
@tree.command(name="announcement", description="Post announcement.")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(content="Message to announce.")
async def announcement(interaction: discord.Interaction, content: str):
    embed = discord.Embed(title="📢 Announcement", description=content, color=0x000000)
    for cid in [ANNOUNCEMENT_CHANNEL_ID, MINI_ANNOUNCEMENT_CHANNEL_ID]:
        channel = bot.get_channel(cid)
        if channel:
            await channel.send("@everyone", embed=embed)
    await interaction.response.send_message("✅ Announcement sent!", ephemeral=True)

# === SNEAK PEEK ===
@tree.command(name="sneak", description="Post a sneak peek.")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(content="Caption", image="Image file")
async def sneak(interaction: discord.Interaction, image: discord.Attachment, content: str = ""):
    embed = discord.Embed(description=content, color=0x000000)
    embed.set_image(url=image.url)
    channel = bot.get_channel(SNEAK_CHANNEL_ID)
    if channel:
        await channel.send("@everyone", embed=embed)
        await interaction.response.send_message("✅ Sneak posted!", ephemeral=True)

# === TWEET ENGAGEMENT ===
@tree.command(name="tweet", description="Send tweet engagement.")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(tweet_link="Tweet URL", engagement_type="Type of engagement")
@app_commands.choices(
    engagement_type=[
        app_commands.Choice(name="❤️ + 🔁", value="like_retweet"),
        app_commands.Choice(name="❤️ + 💬", value="like_comment"),
        app_commands.Choice(name="🔁 + 💬", value="retweet_comment"),
        app_commands.Choice(name="❤️ + 🔁 + 💬", value="all_three"),
    ]
)
async def tweet(interaction: discord.Interaction, tweet_link: str, engagement_type: app_commands.Choice[str]):
    emoji_map = {
        "like_retweet": ["❤️", "🔁"],
        "like_comment": ["❤️", "💬"],
        "retweet_comment": ["🔁", "💬"],
        "all_three": ["❤️", "🔁", "💬"]
    }
    view = discord.ui.View()
    for emoji in emoji_map[engagement_type.value]:
        view.add_item(discord.ui.Button(label=emoji, style=discord.ButtonStyle.link, url=tweet_link))
    channel = bot.get_channel(TWEET_CHANNEL_ID)
    if channel:
        await channel.send(f"@everyone\n{tweet_link}", view=view)
        await interaction.response.send_message("✅ Tweet alert sent!", ephemeral=True)

# === OFFICIAL LINKS ===
@tree.command(name="official", description="Post official message.")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(content="The message to post.")
async def official(interaction: discord.Interaction, content: str):
    embed = discord.Embed(description=content, color=0x000000)
    channel = bot.get_channel(OFFICIAL_LINKS_ID)
    if channel:
        await channel.send("@everyone", embed=embed)
        await interaction.response.send_message("✅ Official message sent!", ephemeral=True)

# === HELP COMMAND ===
@tree.command(name="help", description="List available commands.")
async def help_cmd(interaction: discord.Interaction):
    desc = """
**/game** — Start Rumble Royale
**/rank** — Check your level
**/leaderboard** — View top users

**/sneak** — Post Sneak Peek (Admin only)
**/announcement** — Post Announcements (Admin only)
**/tweet** — Tweet Engagement (Admin only)
**/official** — Post Official Link (Admin only)
"""
    embed = discord.Embed(title="🛠 Command List", description=desc, color=0x000000)
    await interaction.response.send_message(embed=embed, ephemeral=True)

# === ERROR HANDLER ===
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.send_message("❌ You don't have permission.", ephemeral=True)

# === READY EVENT ===
@bot.event
async def on_ready():
    await tree.sync()
    print(f"{bot.user} is online!")

keep_alive()
bot.run(os.environ["DISCORD_TOKEN"])
