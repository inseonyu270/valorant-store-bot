import os
import ssl
import certifi
import aiohttp
import asyncio

os.environ['SSL_CERT_FILE'] = certifi.where()
ssl_context = ssl.create_default_context(cafile=certifi.where())

uris = [
    ("riot-client", "https://auth.riotgames.com/redirect_uri"),
    ("riot-client", "https://playvalorant.com/opt_in"),
    ("rso-page", "https://playvalorant.com/opt_in"),
    ("play-valorant-web-prod", "https://playvalorant.com/opt_in"),
]

async def test_redirects():
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "RiotClient/86.0.1.2017.3088 rso-auth (Windows;10;10.0.19045.1.256.64bit)"
    }
    for cid, uri in uris:
        jar = aiohttp.CookieJar(unsafe=True)
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        async with aiohttp.ClientSession(cookie_jar=jar, headers=headers, connector=connector) as session:
            body_init = {
                "client_id": cid,
                "nonce": "1",
                "redirect_uri": uri,
                "response_type": "token id_token",
                "scope": "openid account"
            }
            async with session.post("https://auth.riotgames.com/api/v1/authorization", json=body_init) as resp:
                print(f"CID {cid} URI {uri} -> Status: {resp.status}, JSON: {await resp.json()}")

asyncio.run(test_redirects())
