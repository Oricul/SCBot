# Import required modules.
import json
import aiohttp

# This class is responsible for creating goo.gl using the Google API.
# It requires an API key.
# Special thanks to Protty.
class Shortener:
    # shorten takes the Google API key and the URL to shorten.
    async def shorten(api,url):
        # Create our aiohttp session.
        session = aiohttp.ClientSession()
        # Compile our post url with API key.
        postURL = 'https://www.googleapis.com/urlshortener/v1/url?key={}'.format(api)
        # Compile our URL to shorten.
        payload = {'longUrl': url}
        # What kind of response do we want? JSON!
        headers = {'content-type': 'application/json'}
        # Use async with aiohttp to request a response from Google's API.
        # Await the response, close the session and return the response.
        async with session.post(postURL,data=json.dumps(payload),headers=headers) as resp:
            found = (await resp.json())['id']
            session.close()
            return found