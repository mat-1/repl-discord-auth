from aiohttp import web
import asyncio
import commands
from jinja2 import Environment, FileSystemLoader, select_autoescape
import database
import aiohttp
import os
import replit

routes = web.RouteTableDef()


with open('site_url.txt', 'r') as f:
	base_url = f.read()

jinja_env = Environment(
	loader=FileSystemLoader(searchpath='templates'),
	autoescape=select_autoescape(['html', 'xml']),
	enable_async=True,
	extensions=[],
	trim_blocks=True,
	lstrip_blocks=True
)
jinja_env.globals['base_url'] = base_url


async def load_template(filename, **kwargs):
	if not hasattr(load_template, 'template_dict'):
		load_template.template_dict = {}
	if filename in load_template.template_dict:
		t = load_template.template_dict[filename]
	else:
		t = jinja_env.get_template(filename)
		load_template.template_dict[filename] = t
	r = await t.render_async(**kwargs)
	return r


@routes.get('/')
async def index(request):
	return web.Response(
		text=await load_template(
			'index.html',
		),
		content_type='text/html'
	)

@routes.get('/api')
async def api_docs(request):
	return web.Response(
		text=await load_template(
			'apidocs.html',
		),
		content_type='text/html'
	)

@routes.get('/discord')
async def discord_redirect(request):
	return web.HTTPFound('https://discord.gg/d2QWXwG')

CLIENT_ID = 661059921629937694
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
REDIRECT_URI = 'https://auth.repl.co/verify'

@routes.get('/auth')
async def auth_redirect(request):
	return web.HTTPFound(
		f'https://discordapp.com/oauth2/authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope=identify'
	)

@routes.get('/verify')
async def verify(request):
	code = request.query.get('code')
	if not code:
		return web.HTTPFound('/auth')
	async with aiohttp.ClientSession() as s:
		r = await s.post(
			'https://discordapp.com/api/v6/oauth2/token',
			data={
				'client_id': CLIENT_ID,
				'client_secret': CLIENT_SECRET,
				'grant_type': 'authorization_code',
				'code': code,
				'redirect_uri': REDIRECT_URI,
				'scope': 'identify',
			}
		)
		data = await r.json()
		if 'error' in data:
			return web.HTTPFound('/auth')
		access_token = data['access_token']
		r = await s.get(
			'https://discordapp.com/api/users/@me',
			headers={
				'Authorization': 'Bearer ' + access_token
			}
		)
		data = await r.json()
		user_id = int(data['id'])
		new_uuid = await commands.create_link_uuid(user_id)
	return web.HTTPFound('/' + new_uuid)

@routes.get('/{uuid}')
async def link_acc_web(request):
	link_uuid = request.match_info['uuid']
	if link_uuid in commands.link_url_uuids:
		return web.Response(
			text=await load_template(
				'link.html'
			),
			content_type='text/html'
		)
	link_data = await database.check_link_uuid(link_uuid)
	if link_data is not None:
		return web.Response(
			text=await load_template(
				'link.html'
			),
			content_type='text/html'
		)
	return web.HTTPNotFound()

@routes.get('/linked/{uuid}')
async def linked_acc_web(request):
	link_uuid = request.match_info['uuid']
	user_id = request.headers['X-Replit-User-Id']
	user_name = request.headers['X-Replit-User-Name']

	if not user_id:
		return web.HTTPTemporaryRedirect('/{uuid}')
	if link_uuid in commands.link_url_uuids:
		link_data = commands.link_url_uuids[link_uuid]
		discord_uuid = int(link_data['discord'])
		discord_channel = link_data['discord_channel']

		await database.new_user(discord_uuid, user_name, link_uuid)
		if discord_channel:
			await discord_channel.send(f'Linked <@{discord_uuid}> with <https://repl.it/@{user_name}>')
		for guild in app.discord.guilds:
			member = guild.get_member(discord_uuid)
			if not member: continue
			role_id = await database.check_verified_role(guild.id)
			if role_id:
				role = guild.get_role(role_id)
				await member.add_roles(role)
		del commands.link_url_uuids[link_uuid]
	else:
		link_data = await database.check_link_uuid(link_uuid)
		if link_data is None:
			return web.HTTPTemporaryRedirect('/auth')
		discord_uuid = link_data['discord_uuid']
		replit_username = link_data['replit_username']
		if replit_username != user_name:
			return web.HTTPTemporaryRedirect('/{uuid}')
	discord_user = app.discord.get_user(discord_uuid)
	discord_username = str(discord_user or '???')
	return web.Response(
		text=await load_template(
			'linked.html',
			replit_username=user_name,
			discord_username=discord_username,
			discord_uuid=discord_uuid
		),
		content_type='text/html'
	)

@routes.get('/avatar/discord/{uuid}')
async def discordavatar(request):
	discord_uuid = int(request.match_info['uuid'])
	discord_user = app.discord.get_user(discord_uuid)
	if not discord_user:
		return
	data = await discord_user.avatar_url_as(format='png', size=64).read()
	return web.Response(
		body=data,
		content_type='image/png'
	)

@routes.get('/avatar/replit/{username}')
async def discordavatar(request):
	username = request.match_info['username']
	async with aiohttp.ClientSession() as s:
		async with s.post(
			'https://repl.it/graphql',
			json={
				'operationName': 'UserInfoCard',
				'query': 'query UserInfoCard($username: String!) { userByUsername(username: $username) { image }}',
				'variables': {
					'username': username
				}
			},
			headers={
				'X-Requested-With': 'Discord Repl link bot',
				'referer': 'https://repl.it'
			}
		) as r:
			profile_data = await r.json()
			avatar_url = profile_data['data']['userByUsername']['image']
		async with s.get(avatar_url) as r:
			data = await r.read()
			content_type = r.content_type
	return web.Response(
		body=data,
		content_type=content_type
	)

@routes.get('/api/discord/{uuid}')
async def api_replit_from_discord(request):
	discord_uuid = int(request.match_info['uuid'])
	data = await database.check_discord_uuid(discord_uuid, string=True)
	if not data: return web.json_response({})
	return web.json_response({
		'replit_username': data['replit_username'],
		'discord_ids': data['discord_uuids']
	})

@routes.get('/api/replit/{username}')
async def api_discord_from_replit(request):
	replit_username = request.match_info['username']
	data = await database.check_replit_username(replit_username, string=True)
	if not data: return web.json_response({})
	return web.json_response({
		'replit_username': data['replit_username'],
		'discord_ids': data['discord_uuids']
	})

@routes.get('/api/rich/discord/{uuid}')
async def api_rich_replit_from_discord(request):
	discord_uuid = int(request.match_info['uuid'])
	data = await database.check_discord_uuid(discord_uuid, string=True)
	if not data: return web.json_response({})
	replit_username = data['replit_username']
	replit_data = await replit.get_user_info(replit_username)
	return web.json_response({
		'replit_username': replit_username,
		'discord_ids': data['discord_uuids'],
		**replit_data
	})

@routes.get('/api/rich/replit/{username}')
async def api_rich_discord_from_replit(request):
	replit_username = request.match_info['username']
	data = await database.check_replit_username(replit_username, string=True)
	if not data: return web.json_response({})
	replit_data = await replit.get_user_info(replit_username)
	return web.json_response({
		'replit_username': replit_username,
		'discord_ids': data['discord_uuids'],
		**replit_data
	})



def start_server(loop, background_task, client):
	#app.discord = client
	global app
	asyncio.set_event_loop(loop)
	app = web.Application(
		middlewares=[]
	)
	app.discord = client
	app.add_routes([web.static('/static', 'static')])
	app.add_routes(routes)
	asyncio.ensure_future(
		background_task,
		loop=loop
	)
	web.run_app(
		app,
		port=8080
	)
