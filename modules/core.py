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
    async def market(self, ctx, shipName, ccuFrom=None):
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
        await self.bot.delete_message(ctx.message)
        compiledList = []
        # Submit a processing notification - since this command takes a while.
        notifembed = discord.Embed(title="Processing...", colour=discord.Colour(0xFFFF00),
                                  description="This may take a moment...")
        notifembed.set_author(name=ctx.message.author.name, icon_url=ctx.message.author.avatar_url)
        notifMSG = await self.bot.say(embed=notifembed)
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
        data = BeautifulSoup(urlopen("http://mrfats.mobiglas.com/search?f={}&h=true&s=price&q={}".format(searchType, shipName)), "html.parser")
        # We only want two data sets. 'page' gives us the page number. 'data' is, well data.
        page = data.select("tr")
        data = data.select("li")
        # If there's no data in 'page', then we got some kind of resolution error. Break the loop.
        # Error for this is handled later as a general fail.
        if not (len(page) > 0):
            return
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
            # We need some blank variables.
            colOne = ""
            colTwo = ""
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
                    embed.set_image(url=eIMG)
                    # Try to send the embed. If it fails, log why.
                    try:
                        await self.bot.delete_message(notifMSG)
                        await self.bot.say(embed=embed)
                    except Exception as e:
                        print("PRE - Exception: ''{}'' Length: ''{}'' Process stopped.".format(e, calcLength))
                    return
                # Now let's add content to our columns. If they've defined a CCU FROM craft, then only add those.
                if (ccuFrom and ccuFrom.lower() in j[0].lower()) or not (ccuFrom):
                        colOne = "{}[{}]({})  \n".format(colOne,j[0],j[3])
                        colTwo = "{}{} ({})\n".format(colTwo,j[2],j[1])
            # We're outside the loop now! Let's prepare our embed. If limiter is not triggered, then add the
            # headers. If it has been, then we just need to set the color.
            embed = discord.Embed(title=eTitle, colour=discord.Colour(0x00ECFF), url=eURL, description=eDesc)
            embed.set_author(name=eaName, icon_url=eaIcon)
            embed.add_field(name="Package", value=colOne, inline=True)
            embed.add_field(name="Price (User)", value=colTwo, inline=True)
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
        await self.bot.delete_message(notifMSG)

    @commands.command(pass_context=True)
    async def ship(self,ctx,*,ship):
        '''Displays Star Citizen ship information.
                Examples:
                    Search for ship: sc.ship mustang alpha
                    Search for series: sc.ship mustang'''
        print("[{}] <{},{}> {} ({}), '{}'".format(ctx.message.timestamp, ctx.message.server.id, ctx.message.channel.id,
                                                  ctx.message.author.name, ctx.message.author.id, ctx.message.content))
        await self.bot.delete_message(ctx.message)
        # Submit a processing notification - since this command takes a while.
        notifembed = discord.Embed(title="Processing...", colour=discord.Colour(0xFFFF00),
                                   description="This may take a moment...")
        notifembed.set_author(name=ctx.message.author.name, icon_url=ctx.message.author.avatar_url)
        notifMSG = await self.bot.say(embed=notifembed)
        fixShip = ship.title()
        try:
            fixShip = re.sub(' ','_',fixShip)
            data = BeautifulSoup(urlopen("https://starcitizen.tools/{}".format(fixShip)), "html.parser")
        except Exception as e:
            capt = e
            print("Outter Exception: {}".format(capt))
            if '404' in str(capt):
                parseShip = re.split(' ',ship)
                secErr = ""
                for i in parseShip:
                    print(secErr)
                    secErr = ""
                    try:
                        data = BeautifulSoup(urlopen("https://starcitizen.tools/{}".format(i)), "html.parser")
                        fixShip = i
                        break
                    except Exception as err:
                        secErr = err
                        print("Inner Exception: {}".format(secErr))
                        pass
                if (secErr):
                    await self.bot.delete_message(notifMSG)
                    await self.bot.say("Your search is invalid, or returned no results.")
                    return
                else:
                    pass
            else:
                await self.bot.delete_message(notifMSG)
                await self.bot.say("Some fatal error occurred: {}".format(capt))
                return
        variants = data.select("li.toclevel-1")
        data = data.select("table.infobox-table")
        for d in data:
            selectName = d.select("th.infobox-table-name.fn")
            if (len(selectName) == 0):
                selectName = d.select("th.infobox-table-name")
            selectName = re.split('[<>]', str(selectName))
            if 'series' in selectName[2].lower():
                for v in variants:
                    selectVar = v.select("span.toctext")
                    selectVar = re.split('[<>]',str(selectVar))
                    if ('references' not in selectVar[2].lower()):
                        vCount = 0
                        selectVariants = ""
                        while (vCount < len(selectVar)):
                            if '{}'.format(fixShip.lower()) in selectVar[vCount].lower():
                                selectVariants = '{}{}\n'.format(selectVariants,selectVar[vCount])
                            vCount += 1
            selectName = selectName[2]
            selectFields = d.select("td")
            selectFields = re.split('[<>]', str(selectFields))
            selectCounter = 0
            compileit = ""
            for c in selectFields:
                selectCounter += 1
                compileit = "{}({}) {}\n".format(compileit,selectCounter,c)
                if 'manufacturer' in c.lower():
                    selectManufacturer = selectFields[selectCounter + 5]
                    selectShort = selectFields[selectCounter + 11]
                    print("Manufacturer: {} {}".format(selectFields[selectCounter+5],selectFields[selectCounter+11]))
                    selectManufacturer = '{} {}'.format(selectManufacturer, selectShort)
                    continue
                if 'focus' in c.lower():
                    if 'selectFocus' not in locals():
                        selectFocus = "{}\n".format(selectFields[selectCounter + 3])
                    else:
                        selectFocus = "{}{}\n".format(selectFocus,selectFields[selectCounter +3 ])
                    print("Focus: {}".format(selectFields[selectCounter+3]))
                    continue
                if 'production state' in c.lower():
                    if 'active' in str(selectFields[selectCounter + 3]).lower():
                        selectStatus = "{}{}".format(selectFields[selectCounter + 3],selectFields[selectCounter + 5])
                    else:
                        selectStatus = selectFields[selectCounter + 3]
                    print("Prod. State: {}\nProd. Color: {}".format(selectFields[selectCounter + 3],selectFields[selectCounter + 2]))
                    selectColor = re.split('[#|;]', selectFields[selectCounter + 2])
                    continue
                if 'maximum crew' in c.lower():
                    print("Max. Crew: {}".format(selectFields[selectCounter + 3]))
                    selectCrew = selectFields[selectCounter + 3]
                    continue
                if 'pledge cost' in c.lower():
                    print("Cost: {}".format(selectFields[selectCounter + 3]))
                    selectPrice = selectFields[selectCounter + 3]
                    if '$' not in selectPrice:
                        selectPrice = "$ {}".format(selectPrice)
                    continue
                if 'null-cargo mass' in c.lower():
                    print("Mass: {}".format(selectFields[selectCounter + 3]))
                    selectMass = selectFields[selectCounter + 3]
                    continue
                if 'max. scm speed' in c.lower():
                    print("Max. SCM Speed: {}".format(selectFields[selectCounter + 3]))
                    selectSCMSpeed = selectFields[selectCounter + 3]
                    continue
                if 'length' in c.lower():
                    print("Length: {}".format(selectFields[selectCounter + 3]))
                    selectLength = selectFields[selectCounter + 3]
                    continue
                if 'height' in c.lower():
                    if '/td' not in selectFields[selectCounter + 3]:
                        print("Height: {}".format(selectFields[selectCounter + 3]))
                        selectHeight = selectFields[selectCounter + 3]
                        continue
                if 'beam' in c.lower():
                    print("Width: {}".format(selectFields[selectCounter + 3]))
                    selectWidth = selectFields[selectCounter + 3]
                    continue
                if 'max. afterburner speed' in c.lower():
                    print("Max. AB Speed: {}".format(selectFields[selectCounter + 3]))
                    selectABSpeed = selectFields[selectCounter + 3]
                    continue
                if 'cargo capacity' in c.lower():
                    print("Cargo: {}".format(selectFields[selectCounter + 3]))
                    selectCargo = selectFields[selectCounter + 3]
                    continue
            #print(compileit)
            selectImage = d.select_one("img")
            selectImage = re.split('[<>"]',str(selectImage))
        if (len(selectColor[2]) <= 6):
            eColor = selectColor[2]
        else:
            eColor = 'ff0000'
        embed = discord.Embed(title="{}".format(selectName),colour=discord.Colour('{}'.format(int(eColor,16))),
                              url="https://starcitizen.tools/{}".format(fixShip),
                              description="{}".format(selectManufacturer))
        embed.set_author(name=ctx.message.author.name, icon_url=ctx.message.author.avatar_url)
        embed.set_image(url="https://starcitizen.tools{}".format(selectImage[10]))
        if 'selectFocus' in locals():
            embed.add_field(name="Focus", value=selectFocus, inline=True)
        if 'selectStatus' in locals():
            embed.add_field(name="Status", value=selectStatus, inline=True)
        if 'selectHeight' in locals():
            embed.add_field(name="Height", value=selectHeight, inline=True)
        if 'selectWidth' in locals():
            embed.add_field(name="Width", value=selectWidth, inline=True)
        if 'selectLength' in locals():
            embed.add_field(name="Length", value=selectLength, inline=True)
        if 'selectMass' in locals():
            embed.add_field(name="Mass", value=selectMass, inline=True)
        if 'selectCargo' in locals():
            embed.add_field(name="Cargo", value=selectCargo, inline=True)
        if 'selectCrew' in locals():
            embed.add_field(name="Crew", value=selectCrew, inline=True)
        if 'selectSCMSpeed' in locals():
            embed.add_field(name="Max. SCM Speed", value=selectSCMSpeed, inline=True)
        if 'selectABSpeed' in locals():
            embed.add_field(name="Max. Afterburner Speed", value=selectABSpeed, inline=True)
        if 'selectPrice' in locals():
            embed.add_field(name="Cost", value=selectPrice, inline=True)
        if 'selectVariants' in locals():
            embed.add_field(name="Variants", value=selectVariants, inline=True)
        try:
            await self.bot.say(embed=embed)
        except Exception as e:
            await self.bot.say(e)
        await self.bot.delete_message(notifMSG)


# Add cog to bot once loaded.
def setup(bot):
    bot.add_cog(StarCitizen(bot))