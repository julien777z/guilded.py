# This is a development branch

This is not the main branch of guilded.py. Breaking changes ensue. This branch is not on PyPI. Please [join the Guilded API server](https://community.guildedapi.com) to give feedback (#library-list, guilded.py role).

# API

This branch uses the early access official API, not the client API. For a version of this library made for userbots, see [1.0.0](https://github.com/shayypy/guilded.py/tree/1.0.0).

# Basic Example

```py
import guilded

client = guilded.Client('f7214a8b-f6db-11eb-b2b9-7085c2bfddec')

@client.event
async def on_ready():
    print('Ready')

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    if message.content == 'ping':
        await message.channel.send('pong')

client.run('KsdfifhsWFeaAFiobEfndsfv9HFuisdjFDkasdfjsdfIEuwaq/sfdMSfsoqPfdspfSoawJdfuvdyEbrnm/w==')
```
