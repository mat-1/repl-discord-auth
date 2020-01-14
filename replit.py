import aiohttp

async def get_user_info(username):
	async with aiohttp.ClientSession() as s:
		async with s.post(
			'https://repl.it/graphql',
			json={
				'operationName': 'userByUsername',
				'query': '''
				query userByUsername($username: String!, $pinnedReplsFirst: Boolean, $count: Int) {
					userByUsername(username: $username) {
						image
						karma
						repls: publicRepls(
							pinnedReplsFirst: $pinnedReplsFirst, count: $count
						) {
							items {
								url
								title
								lang: languageDisplayName
							}
						}
					}
				}
				''',
				'variables': {
					'username': username,
					'pinnedReplsFirst': False,
					'count': 3
				}
			},
			headers={
				'X-Requested-With': 'Discord Repl link bot',
				'referer': 'https://repl.it'
			}
		) as r:
			data = await r.json()
			data = data['data']['userByUsername']
			if data is None: return
			data['cycles'] = data['karma']
			del data['karma']
			data['avatar'] = data['image']
			del data['image']

			data['repls'] = data['repls']['items']
			return data