# Required Modules
import re
from urllib.request import urlopen
import discord
import json
from bs4 import BeautifulSoup
from discord.ext import commands
from .printoverride import print as print
from .gShortURL import Shortener

# Import Google API key from JSON (not shared to GitHub). If it's not there, the script will not run.
# JSON structure:
# {
#         "bot": {
#                 "token": "DISCORD TOKEN",
#                 "ownerid": "OWNER DISCORD ID",
#                 "Google": "GOOGLE API KEY"
#         }
# }
jsonfile = "SCBot"
try:
    with open('./{}.json'.format(jsonfile), 'r+') as secFile:
        sec = json.load(secFile)
        gAPI = sec['bot']['Google']
except FileNotFoundError:
    exit("{}.json is not in the current bot directory.".format(jsonfile))

# Shorten links for posts and images. Useful for getting more content in a single embed.
async def shortURL(link):
    try:
        return (await Shortener.shorten(gAPI,link))
    except Exception as e:
        print("Google API failure.\nError: {0}\nTrying again...".format(e))
        pass
    try:
        return (await Shortener.shorten(gAPI,link))
    except Exception as ee:
        print("Google API failure, again.\nError: {0}\nReturning as an error.".format(ee))
        return "ERROR"

# Discord COG starts here.
class StarCitizen:
    def __init__(self, bot):
        self.bot = bot

    # Market command
    @commands.command(pass_context=True)
    async def market(self, ctx, shipName, ccuFrom=None, maxPage=1):
        '''Displays MrFats results for a defined ship.
        Examples:
            Search for Carrack: sc.market carrack
            Search for Carrack CCU from Aquila: sc.market carrack aquila
            Search for Carrack, no CCUs: sc.market carrack no
            Search for Carrack, only CCUs: sc.market carrack yes

        Note: This command is slow until I implement a SQL database. Sorry!'''
        # Print the query for logging purposes.
        print("[{}] <{},{}> {} ({}), '{}'".format(ctx.message.timestamp,ctx.message.server.id,ctx.message.channel.id,
                                                  ctx.message.author.name,ctx.message.author.id,ctx.message.content))
        # Limit the query to a max of 3 pages. It's spammy enough with 1 page.
        if int(maxPage) >= 3:
            await self.bot.say("Sorry, that's too many pages.")
        else:
            # Use i to track our page number. Compiled List needs to be preset, so do it here.
            i = 1
            compiledList = []
            # While loop to gather all data we need from pages.
            while i <= int(maxPage):
                # Set our search type, then reset the ccuFrom variable for parsing later.
                if ccuFrom == "no":
                    searchType = "ship"
                    ccuFrom = None
                elif ccuFrom == "yes":
                    searchType = "ccu"
                    ccuFrom = None
                else:
                    searchType = "shipandccu"
                # Use BS4 to open the page and make it usable.
                data = BeautifulSoup(urlopen("http://mrfats.mobiglas.com/search?f={}&h=true&s=price&page={}&q={}".format(searchType, i, shipName)), "html.parser")
                # We only want two data sets. 'page' gives us the page number. 'data' is, well data.
                page = data.select("tr")
                data = data.select("li")
                # If there's no data in 'page', then we got some kind of resolution error. Break the loop.
                # Error for this is handled later as a general fail.
                if not (len(page) > 0):
                    break
                # Find the page number. If the page number is different from 'i', then this is not a real page.
                # We break and allow the code to either complete or fail.
                for p in page:
                    pageNum = p.select_one("td.cur")
                    if pageNum:
                        fixedPageNum = int(re.split('[ ]', str(re.split('</span>|[\n\t]', str(pageNum))[4]))[1])
                        compPage = i - fixedPageNum
                        break
                # Because we use a for loop above, we need to re-test this variable. If it's anything but zero,
                # then it's not a real page. Break.
                # If there's an exception, we didn't reach a correct page - break.
                try:
                    if compPage:
                        break
                except:
                    break
                # MAGIC HAPPENS HERE.
                for d in data:
                    # Variables are self-explanatory. We use BS4 to select specifics for parsing.
                    selectName = d.select_one("div.clickable.nobr")
                    selectPrice = d.select_one("div.price.nobr")
                    selectShip = d.select_one("h1")
                    selectTag = d.select_one("span.listing-tag")
                    selectIMG = d.select_one("img.vcenter-image")
                    selectLink = d.select("a.header-right.small.button")
                    # Poor coding maybe, but we get a lot of 'None' hits in 'selectPrice'. If it's 'None', ignore it.
                    if selectPrice:
                        # Again, maybe poor coding, but we need to part a link if we can find it.
                        if selectLink:
                            # Remove HTML tags from our link and select it from the resulting list.
                            postLink = str(re.split('[<>"]',str(selectLink[1]))[4])
                            # Use Google to shorten the URL. If there's an API fail, just link the results page.
                            postLink = await shortURL(postLink)
                            if 'ERROR' in postLink:
                                postLink = "http://mrfats.mobiglas.com/search?f={}&h=true&s=price&q={}".format(searchType,shipName)
                        # Another example of my shoddy coding. If there's an image, let's use it.
                        if selectIMG:
                            # Remove HTML tags from our image.
                            fixIMG = re.split('[<>"]',str(selectIMG))
                            # Some images result in an 'Unavailable.jpg'. Ignore those results.
                            if 'unavailable' not in fixIMG[4].lower():
                                # Setup variable, and then shorten the image URL. If it fails, then we'll use unavailable.
                                shipIMG = fixIMG[4]
                                shipIMG = await shortURL(shipIMG)
                                if 'ERROR' in shipIMG:
                                    shipIMG = "https://robertsspaceindustries.com/media/ov5oe73cnqyrhr/store_small/Unavailable.jpg"
                        # Here's the shoddiness again!
                        if selectTag:
                            # We need to cycle through all the tags.
                            for t in selectTag:
                                # Remove HTML from our tags.
                                fixTag = re.split('[<>]', str(t))
                                # We want to ignore the 'blackmarket' tagged results. They're sketchy.
                                # Perhaps allow the user to choose this at a later time.
                                # The break here is only for our 'for' loop. We'll need to use another check to break
                                # the current iteration. If the variable doesn't contain 'blackmarket', then it's not
                                # present at all.
                                if 'blackmarket' in fixTag:
                                    break
                        try:
                            if 'blackmarket' in fixTag:
                                continue
                        except:
                            pass
                        # Remove HTML tags from our user name, price and ship name. We also need to do a bit of
                        # parsing on the ship name.
                        fixName = re.split('[<>]', str(selectName))
                        fixPrice = re.split('[<>]', str(selectPrice))
                        prefixShip = re.split('[<>]|[\t]{2,}|[\n]', str(selectShip))
                        fixShip = "{}".format(prefixShip[4])
                        # If 'CCU' is in the ship name, we need to grab the 'CCU FROM' line.
                        if 'CCU' in fixShip:
                            fixShip = "{}{}".format(fixShip, prefixShip[6])
                        # Some sellers will list for $0.00 to trick the system. To teach them a lesson, we ignore them.
                        if not '$0.00' in fixPrice[2]:
                            compiledList.append([fixShip, fixName[2], fixPrice[2], postLink])
                # Keep our page count going. Loop happens here.
                i += 1
            # POST LOOP. If 'compiledList' is greater than 0, we have results to show.
            if len(compiledList) > 0:
                # Make the description readable for humans.
                if 'shipandccu' in searchType:
                    eDesc = "Ships and CCUs"
                elif 'ship' in searchType:
                    eDesc = "Ships"
                else:
                    eDesc = "CCUs"
                # Predefine embed parts that we'll use later. This is useful for checking lengths.
                eTitle = "{}".format(shipName.title())
                eURL = "http://mrfats.mobiglas.com/search?f={}&h=true&s=price&q={}".format(searchType, shipName)
                eaName = "{}".format(ctx.message.author.name)
                eaIcon = "{}".format(ctx.message.author.avatar_url)
                # We try to grab the 'shipIMG' URL. This may not be set at times if there are no proper images.
                # So we use a TRY to set it.
                try:
                    if shipIMG:
                        eIMG = "{}".format(shipIMG)
                    else:
                        eIMG = "https://robertsspaceindustries.com/media/ov5oe73cnqyrhr/store_small/Unavailable.jpg"
                except:
                    pass
                # We need some blank variables. 'limiter' is used for determining if our embed needs a header.
                # We don't place a header on 2nd+ posts to make it look more fluid.
                colOne = ""
                colTwo = ""
                limiter = 0
                # If there's content in compiledList, let's loop through it.
                for j in compiledList:
                    # Calculate the length of our embed as best as we can. You can't len(embed) :(
                    calcLength = len(eDesc)+len(eTitle)+len(eURL)+len(eaName)+len(eaIcon)+len(eIMG)+len(colOne)+len(colTwo)+100
                    # Check if our embed is getting too long. If it is, immediately make a post and clear variables.
                    # Of note, the limit of a single post in Discord is 2000 characters. However, embeds add
                    # character length that we can't calculate. It seems variable, so keep this low to prevent
                    # '400' errors.
                    if (calcLength) >= 1500:
                        # Setup our shortened embed. There is no image here.
                        embed = discord.Embed(title=eTitle, colour=discord.Colour(0x00ECFF), url=eURL, description=eDesc)
                        embed.set_author(name=eaName, icon_url=eaIcon)
                        embed.add_field(name="Package", value=colOne, inline=True)
                        embed.add_field(name="Price (User)", value=colTwo, inline=True)
                        # Try to send the embed. If it fails, log why.
                        try:
                            await self.bot.say(embed=embed)
                        except Exception as e:
                            print("PRE - Exception: ''{}'' Length: ''{}'' Process stopped.".format(e, calcLength))
                            return
                        # Clear those variables and set our limiter to 1. Even if this gets triggered multiple times
                        # it won't matter. We just need limiter to be 1 or 0.
                        colOne = ""
                        colTwo = ""
                        limiter = 1
                    # Now let's add content to our columns. If they've defined a CCU FROM craft, then only add those.
                    if (ccuFrom and ccuFrom.lower() in j[0].lower()) or not (ccuFrom):
                            colOne = "{}[{}]({})  \n".format(colOne,j[0],j[3])
                            colTwo = "{}{} ({})\n".format(colTwo,j[2],j[1])
                # We're outside the loop now! Let's prepare our embed. If limiter is not triggered, then add the
                # headers. If it has been, then we just need to set the color.
                if not limiter:
                    embed = discord.Embed(title=eTitle, colour=discord.Colour(0x00ECFF), url=eURL, description=eDesc)
                    embed.set_author(name=eaName, icon_url=eaIcon)
                else:
                    embed = discord.Embed(colour=discord.Colour(0x00ECFF))
                embed.add_field(name="Package", value=colOne, inline=True)
                embed.add_field(name="Price (User)", value=colTwo, inline=True)
                # This is our last post, so we include the image.
                embed.set_image(url=eIMG)
                # Recalculate length. Use this for error logging.
                calcLength = len(eDesc) + len(eTitle) + len(eURL) + len(eaName) + len(eaIcon) + len(eIMG) + len(colOne) + len(colTwo) + 100
                # Try to send, if not - we probably were '400'd. Log it and length for troubleshooting.
                try:
                    await self.bot.say(embed=embed)
                except Exception as e:
                    print("Exception: ''{}'' Length: ''{}'' Process stopped.".format(e,calcLength))
                    return
            # If there's nothing in 'compiledList', then send our error message.
            else:
                # We make this human friendly, just for niceness sake.
                if 'shipandccu' in searchType:
                    eDesc = "Ships and CCUs"
                elif 'ship' in searchType:
                    eDesc = "Ships"
                else:
                    eDesc = "CCUs"
                # Send a simple embed that will never go over 2k characters.
                embed = discord.Embed(title="No results or invalid search.", colour=discord.Colour(0xFF0000),
                                      url="http://mrfats.mobiglas.com/search?f={}&h=true&s=price&q={}".format(searchType,shipName),
                                      description="{}\n".format(eDesc))
                embed.set_author(name="{}".format(ctx.message.author.name),
                                 icon_url="{}".format(ctx.message.author.avatar_url))
                await self.bot.say(embed=embed)

# Add cog to bot once loaded.
def setup(bot):
    bot.add_cog(StarCitizen(bot))