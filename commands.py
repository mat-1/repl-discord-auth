import uuid
import database
import random
import discord
from discordbot import betterbot, client
from discord.ext import commands
import replit

link_url_uuids = {}

with open('site_url.txt', 'r') as f:
	base_url = f.read()



def get_channel_members(channel_id):
	return client.get_channel(channel_id).members

def check_user_id(ctx, arg):
	try:
		member = ctx.guild.get_member(int(arg))
		if member is not None:
			return member
	except ValueError:
		pass


def check_mention(ctx, arg):
	if arg.startswith('<@') and arg[-1] == '>':
		if arg[2] == '!':
			user_id = arg[3:-1]
		else:
			user_id = arg[2:-1]
		try:
			member = ctx.guild.get_member(int(user_id))
			if member is not None:
				return member
		except ValueError:
			pass


def check_name_with_discrim(ctx, arg):
	member = discord.utils.find(
		lambda m: str(m).lower() == arg.lower(),
		get_channel_members(ctx.channel.id)
	)
	return member


def check_name_without_discrim(ctx, arg):
	member = discord.utils.find(
		lambda m: m.name.lower == arg.lower(),
		get_channel_members(ctx.channel.id)
	)
	return member


def check_nickname(ctx, arg):
	member = discord.utils.find(
		lambda m: m.display_name.lower() == arg.lower(),
		get_channel_members(ctx.channel.id)
	)
	return member


def check_name_starts_with(ctx, arg):
	member = discord.utils.find(
		lambda m: m.name.lower().startswith(arg.lower()),
		get_channel_members(ctx.channel.id)
	)
	return member


def check_nickname_starts_with(ctx, arg):
	member = discord.utils.find(
		lambda m: m.display_name.lower().startswith(arg.lower()),
		get_channel_members(ctx.channel.id)
	)
	return member


def check_name_contains(ctx, arg):
	member = discord.utils.find(
		lambda m: arg.lower() in m.name.lower(),
		get_channel_members(ctx.channel.id)
	)
	return member


def check_nickname_contains(ctx, arg):
	member = discord.utils.find(
		lambda m: arg.lower() in m.display_name.lower(),
		get_channel_members(ctx.channel.id)
	)
	return member

class Member(commands.Converter):
	async def convert(self, ctx, arg):
		if arg[0] == '@':
			arg = arg[1:]
		# Check user id
		member = check_user_id(ctx, arg)
		if member is not None:
			return member

		# Check mention
		member = check_mention(ctx, arg)
		if member is not None:
			return member

		# Name + discrim
		member = check_name_with_discrim(ctx, arg)
		if member is not None:
			return member

		# Name
		member = check_name_with_discrim(ctx, arg)
		if member is not None:
			return member

		# Nickname
		member = check_nickname(ctx, arg)
		if member is not None:
			return member

		# Name starts with
		member = check_name_starts_with(ctx, arg)
		if member is not None:
			return member

		# Nickname starts with
		member = check_nickname_starts_with(ctx, arg)
		if member is not None:
			return member

		# Name contains
		member = check_name_contains(ctx, arg)
		if member is not None:
			return member

		# Nickname contains
		member = check_nickname_contains(ctx, arg)
		if member is not None:
			return member





async def create_link_uuid(discord_uuid, channel=None):
	global link_url_uuids
	link_data = await database.get_link_uuids_from_discord(discord_uuid)
	if link_data:
		print(link_data)
		new_uuid = link_data[discord_uuid]
	else:
		new_uuid = str(uuid.uuid4())
	link_url_uuids[new_uuid] = {
		'discord': discord_uuid,
		'discord_channel': channel
	}
	return new_uuid




# ACTUAL COMMANDS START HERE





@betterbot.command(name='link')
async def link(message, *args):
	new_uuid = await create_link_uuid(message.author.id, message.channel)
	try:
		await message.author.send(
			f"Go to this url to link to your Repl.it account {base_url}/{new_uuid}\n**Don't share this link with anyone**"
		)
		if not isinstance(message.channel, discord.DMChannel):
			await message.channel.send(
				random.choice([
					'Check your DMs!',
					'A link is waiting for you in your DMs!',
					'Special Link: Sent! (Check DMs)',
					'***Link has entered the game*** (Check DMs)',
				])
			)
	except Exception as e:
		print(e, type(e))
		await message.channel.send(
			'Something went wrong when sending the message :('
		)

@betterbot.command(name='user', aliases=('username', 'profile'))
async def username(message, checking_user:Member='self'):
	if checking_user == 'self':
		checking_user = message.author
	elif checking_user is None:
		await message.channel.send('Invalid user')
	checking_user_id = checking_user.id
	try:
		link_data = await database.check_discord_uuid(checking_user_id)
		replit_username = link_data['replit_username']
	except:
		if checking_user_id == message.author.id:
			await message.channel.send("You haven't linked your account yet. Run **)link** to do so!")
		else:
			embed = discord.Embed(
				description=f"<@{checking_user_id}> hasn't linked their account yet."
			)
			await message.channel.send(embed=embed)
	else:

		user_info = await replit.get_user_info(replit_username)
		cycles = user_info['cycles']
		repls = user_info['repls']
		avatar = user_info['avatar']

		embed = discord.Embed(
			color=0x7E68CE
		)

		recent_repls = []
		for repl in repls:
			repl_name = repl['title']
			repl_url = 'https://repl.it' + repl['url']
			repl_lang = repl['lang']
			recent_repls.append(
				f'**[{repl_name}]({repl_url})** ({repl_lang})'
			)
		if recent_repls == []:
			recent_repls = ['No repls']
		embed.add_field(
			name='Recent repls',
			value='\n'.join(recent_repls),
			inline=False
		)

		embed.set_author(
			icon_url=avatar,
			url=f'https://repl.it/@{replit_username}',
			name=f'{replit_username} ({cycles})'
		)
		await message.channel.send(embed=embed)


@betterbot.command(name='help')
async def help(message, *args):
	commands = {
		'link': 'Sends you a DM with a link to verify your account',
		'user @user': "Tells you the user's Repl.it name and recent repls"
	}
	
	perms = message.author.permissions_in(message.channel)
	if perms.administrator:
		commands['verifiedrole <roleid>'] = 'Sets the verified role to the specified id (admin only)'
	content = []
	prefix = message.prefix
	for command in commands:
		content.append(
			f'{prefix}**{command}** - {commands[command]}'
		)

	embed = discord.Embed(
		title='Commands',
		description='\n'.join(content)
	)
	await message.send(embed=embed)

@betterbot.command(name='verifiedrole')
@commands.has_permissions(administrator=True)
async def verified_role(message, role_id: int):
	guild = message.guild
	role = guild.get_role(role_id)
	if role:
		await database.set_verified_role(message.guild.id, role.id)
		await message.send("Ok. Adding role to all verified people..")
		count = 0
		async for user_data in database.get_all_verified_users():
			discord_uuid = user_data['discord_uuid']
			member = guild.get_member(discord_uuid)
			if member:
				await member.add_roles(role)
				count += 1
		if count == 1:
			await message.send(f'Added **{role}** to one person')
		else:
			await message.send(f'Added **{role}** to {count} people')
	else:
		await message.send('Invalid role')
