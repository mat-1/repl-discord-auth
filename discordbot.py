import discord
import os
import database
from betterbot import BetterBot

client = discord.Client()



async def start_bot():
	print('starting bot yeet')
	await client.start(os.getenv('token'))

@client.event
async def on_ready():
	print('ready')
	await client.change_presence(
		activity=discord.Game(name=')help')
	)

@client.event
async def on_member_join(member):
	data = await database.check_discord_uuid(member.id)
	if data:
		guild = member.guild
		role_id = await database.check_verified_role(guild.id)
		if role_id:
			role = guild.get_role(role_id)
			await member.add_roles(role)


prefix = ')'

betterbot = BetterBot(
	prefix=prefix,
	bot_id=661059921629937694
)

@client.event
async def on_message(message):
	await betterbot.process_commands(message)
