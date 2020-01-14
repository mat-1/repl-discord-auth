import motor.motor_asyncio
import time
import os

dbuser = os.getenv('dbuser')
dbpassword = os.getenv('dbpassword')

connection_uri = f'mongodb+srv://{dbuser}:{dbpassword}@cluster0-2ixzl.mongodb.net/?retryWrites=true&w=majority'

client = motor.motor_asyncio.AsyncIOMotorClient(connection_uri)

db = client['replit-accounts']

users_coll = db['users']
guilds_coll = db['guilds']


async def new_user(discord_uuid, replit_username, link_uuid):
	new_data = {
		'discord_uuid': discord_uuid,
		'replit_username': replit_username,
	}
	await users_coll.update_one(
		{'_id': link_uuid},
		{'$set': new_data},
		upsert=True
	)

async def check_link_uuid(link_uuid):
	found = await users_coll.find_one({
		'_id': link_uuid
	})
	return found

async def get_replit_username(discord_uuid):
	print('get_replit_username', discord_uuid)
	found = await users_coll.find_one({
		'discord_uuid': discord_uuid
	})
	if found is None: return
	return found['replit_username']

async def check_discord_uuid(discord_uuid, string=False):
	replit_username = await get_replit_username(discord_uuid)
	if not replit_username: return
	return await check_replit_username(replit_username, string=string)

async def check_replit_username(replit_username, string=False):
	data = {
		'replit_username': '',
		'discord_uuids': []
	}
	async for found in users_coll.find({
		'replit_username': replit_username
	}):
		data['replit_username'] = found['replit_username']
		uuid = found['discord_uuid']
		if string: uuid = str(uuid)
		data['discord_uuids'].append(uuid)
	return data

async def get_link_uuids(replit_username):
	discord_ids = {}
	async for found in users_coll.find({
		'replit_username': replit_username
	}):
		uuid = found['discord_uuid']
		discord_ids[uuid] = found['_id']
	return discord_ids

async def get_link_uuids_from_discord(discord_uuid):
	replit_username = await get_replit_username(discord_uuid)
	if not replit_username: return {}
	return await get_link_uuids(replit_username)

async def set_verified_role(guild_uuid, role_uuid):
	new_data = {
		'role_uuid': role_uuid,
	}
	await guilds_coll.update_one(
		{'_id': guild_uuid},
		{'$set': new_data},
		upsert=True
	)

async def check_verified_role(guild_uuid):
	found = await guilds_coll.find_one({
		'_id': int(guild_uuid)
	})
	if found is None: return None
	return found['role_uuid']

async def get_all_verified_users():
	async for user in users_coll.find({}):
		yield user
