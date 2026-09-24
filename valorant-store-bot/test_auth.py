import os
import ssl
import certifi
import aiohttp
import asyncio

os.environ['SSL_CERT_FILE'] = certifi.where()
ssl_context = ssl.create_default_context(cafile=certifi.where())

async def test():
    headers = {
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    jar = aiohttp.CookieJar(unsafe=True)
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    async with aiohttp.ClientSession(cookie_jar=jar, headers=headers, connector=connector) as session:
        body_init = {
            "client_id": "play-valorant-web-prod",
            "nonce": "1",
            "redirect_uri": "https://playvalorant.com/opt_in",
            "response_type": "token id_token",
            "scope": "account openid"
        }
        async with session.post("https://auth.riotgames.com/api/v1/authorization", json=body_init) as resp:
            print("POST Status:", resp.status)
            print("POST JSON:", await resp.json())
            print("Cookies after POST:", [c.key for c in jar])
            print("Response Set-Cookie headers:", resp.headers.getall('Set-Cookie', []))

asyncio.run(test())
