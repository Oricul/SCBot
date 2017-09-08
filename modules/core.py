# Required Modules
import re
from urllib.request import urlopen
import discord
import json
import asyncio
from bs4 import BeautifulSoup
from discord.ext import commands
from pyshorteners import Shortener as short
from .printoverride import print as print

jsonfile = "SCBot"
try:
    with open('./{}.json'.format(jsonfile), 'r+') as secretfile:
        sec = json.load(secretfile)
        gToken = sec['bot']['Google']
except FileNotFoundError:
    exit("{}.json is not in the current bot directory.".format(jsonfile))
urlshort = short('Google', api_key=gToken, timeout=9000)

def shortURL(link):
    try:
        return urlshort.short(link)
    except Exception as e:
        print("Google API failure.\nError: {0}\nTrying again...".format(e))
        pass
    try:
        return urlshort.short(link)
    except Exception as ee:
        print("Google API failure, again.\nError: {0}\nReturning as an error.".format(ee))
        return "ERROR"

class core:
    def __init__(self, bot):
        self.bot = bot

    @commands.command(pass_context=True)
    async def market(self, ctx, shipName, ccuFrom=None, maxPage=1):
        '''Displays MrFats results for a defined ship.
        Examples:
            Search for Carrack: sc.market carrack
            Search for Carrack CCU from Aquila: sc.market carrack aquila
            Search for Carrack, no CCUs: sc.market carrack no
            Search for Carrack, only CCUs: sc.market carrack yes

        Note: This command is slow until I implement a SQL database. Sorry!'''
        print("[{}] <{},{}> {} ({}), '{}'".format(ctx.message.timestamp,ctx.message.server.id,ctx.message.channel.id,
                                                  ctx.message.author.name,ctx.message.author.id,ctx.message.content))
        if int(maxPage) >= 5:
            await self.bot.say("Sorry, that's too many pages.")
        else:
            i = 1
            compiledList = []
            while i <= int(maxPage):
                if ccuFrom == "no":
                    searchType = "ship"
                    ccuFrom = None
                elif ccuFrom == "yes":
                    searchType = "ccu"
                    ccuFrom = None
                else:
                    searchType = "shipandccu"
                data = BeautifulSoup(urlopen("http://mrfats.mobiglas.com/search?f={}&h=true&s=price&page={}&q={}".format(searchType, i, shipName)), "html.parser")
                page = data.select("tr")
                data = data.select("li")
                if not (len(page) > 0):
                    break
                for p in page:
                    pageNum = p.select_one("td.cur")
                    if pageNum:
                        fixedPageNum = int(re.split('[ ]', str(re.split('</span>|[\n\t]', str(pageNum))[4]))[1])
                        compPage = i - fixedPageNum
                        break
                try:
                    if compPage:
                        break
                except:
                    break
                for d in data:
                    selectName = d.select_one("div.clickable.nobr")
                    selectPrice = d.select_one("div.price.nobr")
                    selectShip = d.select_one("h1")
                    selectTag = d.select_one("span.listing-tag")
                    selectIMG = d.select_one("img.vcenter-image")
                    selectLink = d.select("a.header-right.small.button")
                    # Lots of blank returns, so if value is not None
                    if selectPrice:
                        if selectLink:
                            postLink = str(re.split('[<>"]',str(selectLink[1]))[4])
                            #fixLink = await shortURL(postLink)
                            postLink = shortURL(postLink)
                            if 'ERROR' in postLink:
                                postLink = "http://mrfats.mobiglas.com/search?f={}&h=true&s=price&q={}".format(searchType,shipName)
                        if selectIMG:
                            fixIMG = re.split('[<>"]',str(selectIMG))
                            if 'unavailable' not in fixIMG[4].lower():
                                shipIMG = fixIMG[4]
                                #fixIMG = await shortURL(shipIMG)
                                shipIMG = shortURL(shipIMG)
                                if 'ERROR' in shipIMG:
                                    shipIMG = "https://robertsspaceindustries.com/media/ov5oe73cnqyrhr/store_small/Unavailable.jpg"
                        if selectTag:
                            for t in selectTag:
                                fixTag = re.split('[<>]', str(t))
                                if 'blackmarket' in fixTag:
                                    break
                        try:
                            if 'blackmarket' in fixTag:
                                continue
                        except:
                            pass
                        # Remove html tags
                        fixName = re.split('[<>]', str(selectName))
                        fixPrice = re.split('[<>]', str(selectPrice))
                        # Remove html tags, tabs and new lines
                        prefixShip = re.split('[<>]|[\t]{2,}|[\n]', str(selectShip))
                        fixShip = "{}".format(prefixShip[4])
                        # If it's a CCU, find the upgrade source
                        if 'CCU' in fixShip:
                            fixShip = "{}{}".format(fixShip, prefixShip[6])
                        # If seller is trying to trick system, ignore them completely
                        if not '$0.00' in fixPrice[2]:
                            compiledList.append([fixShip, fixName[2], fixPrice[2], postLink])
                i += 1
            if len(compiledList) > 0:
                if 'shipandccu' in searchType:
                    eDesc = "Ships and CCUs"
                elif 'ship' in searchType:
                    eDesc = "Ships"
                else:
                    eDesc = "CCUs"
                eTitle = "{}".format(shipName.title())
                eURL = "http://mrfats.mobiglas.com/search?f={}&h=true&s=price&q={}".format(searchType, shipName)
                eaName = "{}".format(ctx.message.author.name)
                eaIcon = "{}".format(ctx.message.author.avatar_url)
                try:
                    if shipIMG:
                        eIMG = "{}".format(shipIMG)
                    else:
                        eIMG = "https://robertsspaceindustries.com/media/ov5oe73cnqyrhr/store_small/Unavailable.jpg"
                except:
                    pass
                colOne = ""
                colTwo = ""
                limiter = 0
                for j in compiledList:
                    calcLength = len(eDesc)+len(eTitle)+len(eURL)+len(eaName)+len(eaIcon)+len(eIMG)+len(colOne)+len(colTwo)+100
                    if (calcLength) >= 1600:
                        embed = discord.Embed(title=eTitle, colour=discord.Colour(0x00ECFF), url=eURL, description=eDesc)
                        embed.set_author(name=eaName, icon_url=eaIcon)
                        embed.add_field(name="Package", value=colOne, inline=True)
                        embed.add_field(name="Price (User)", value=colTwo, inline=True)
                        try:
                            await self.bot.say(embed=embed)
                        except Exception as e:
                            print("Exception: {}\nProcess stopped.".format(e))
                            return
                        colOne = ""
                        colTwo = ""
                        limiter = 1
                    if (ccuFrom and ccuFrom.lower() in j[0].lower()) or not (ccuFrom):
                            colOne = "{}[{}]({})  \n".format(colOne,j[0],j[3])
                            colTwo = "{}{} ({})\n".format(colTwo,j[2],j[1])
                if not limiter:
                    embed = discord.Embed(title=eTitle, colour=discord.Colour(0x00ECFF), url=eURL, description=eDesc)
                    embed.set_author(name=eaName, icon_url=eaIcon)
                else:
                    embed = discord.Embed(colour=discord.Colour(0x00ECFF))
                embed.add_field(name="Package", value=colOne, inline=True)
                embed.add_field(name="Price (User)", value=colTwo, inline=True)
                embed.set_image(url=eIMG)
                calcLength = len(eDesc) + len(eTitle) + len(eURL) + len(eaName) + len(eaIcon) + len(eIMG) + len(colOne) + len(colTwo) + 100
                try:
                    await self.bot.say(embed=embed)
                except Exception as e:
                    print("Exception: {}\nProcess stopped.".format(e))
                    return
            else:
                if 'shipandccu' in searchType:
                    eDesc = "Ships and CCUs"
                elif 'ship' in searchType:
                    eDesc = "Ships"
                else:
                    eDesc = "CCUs"
                embed = discord.Embed(title="No results or invalid search.", colour=discord.Colour(0xFF0000),
                                      url="http://mrfats.mobiglas.com/search?f={}&h=true&s=price&q={}".format(searchType,shipName),
                                      description="{}\n".format(eDesc))
                embed.set_author(name="{}".format(ctx.message.author.name),
                                 icon_url="{}".format(ctx.message.author.avatar_url))
                await self.bot.say(embed=embed)

def setup(bot):
    bot.add_cog(core(bot))