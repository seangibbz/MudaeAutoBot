import discord
import re
import asyncio
import json
import time
import logging
import threading
from os.path import join as pathjoin
from collections import OrderedDict

class CacheDict(OrderedDict):
    def __init__(self, *args, **kwds):
        self.max = kwds.pop("max", None)
        OrderedDict.__init__(self, *args, **kwds)
        self._check_size_limit()

    def __setitem__(self, key, value):
        OrderedDict.__setitem__(self, key, value)
        self._check_size_limit()

    def _check_size_limit(self):
        if self.max is not None:
            while len(self) > self.max:
                self.popitem(last=False)

msg_buf = CacheDict(max=50)

jsonf = open("Settings_Mudae.json",encoding="utf-8")
settings = json.load(jsonf)
jsonf.close()


mudae = 432610292342587392
use_emoji = "❤️"

with open("cmds.txt","r",encoding="utf-8") as f:
    mudae_cmds = [line.rstrip() for line in f]
mhids = [int(mh) for mh in settings["channel_ids"]]
shids = [int(sh) for sh in settings["slash_ids"]]
ghids = [int(gh) for gh in settings["slash_guild_ids"]]
channel_settings = dict()

series_list = settings["series_list"]
chars = [charsv.lower() for charsv in settings["namelist"]]
kak_min = settings["min_kak"]
roll_prefix = settings["roll_this"]
sniping = settings.get("sniping_enabled",True)

kakdelayjson = settings["kak_delay"]
claimdelayjson = settings["claim_delay"]

mention_finder = re.compile(r'\<@(?:!)?(\d+)\>')
pagination_finder = re.compile(r'\d+ / \d+')

kak_finder = re.compile(r'\*\*??([0-9]+)\*\*<:kakera:469835869059153940>')
like_finder = re.compile(r'Likes\: \#??([0-9]+)')
claim_finder = re.compile(r'Claims\: \#??([0-9]+)')
poke_finder = re.compile(r'\*\*(?:([0-9+])h )?([0-9]+)\*\* min')
wait_finder = re.compile(r'\*\*(?:([0-9+])h )?([0-9]+)\*\* min \w')
waitk_finder = re.compile(r'\*\*(?:([0-9+])h )?([0-9]+)\*\* min')
ser_finder = re.compile(r'.*.')

KakeraVari = [kakerav.lower() for kakerav in settings["emoji_list"]]
#soulLink = ["kakeraR","KakeraO"]
eventlist = ["🕯️","😆"]

#Last min Claims
is_last_enable = True if settings["Last_True"].lower().strip() == "true" else False 
last_claim_window = settings["last_claim_min"]
min_kak_last = settings["min_kak_last_min"]

kakera_wall = {}
waifu_wall = {}

#logging settings
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s:%(message)s')
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)

default_settings_if_no_settings = f"""🛠️ __**Server Settings**__ 🛠️
             (Server not premium)

            · Prefix: **$** ($prefix)
            · Lang: **en** ($lang)
            · Claim reset: every **180** min. ($setclaim)
            · Exact minute of the reset: xx:**56** ($setinterval)
            · Reset shifted: by +**0** min. ($shifthour)
            · Rolls per hour: **10** ($setrolls)
            · Time before the claim reaction expires: **30** sec. ($settimer)
            · Spawn rarity multiplicator for already claimed characters: **2** ($setrare)
            · % kakera bonus: **+0** ($setkakerabonus)
            · Game mode: **1** ($gamemode)
            · This channel instance: **1** ($channelinstance)
            · Slash commands: enabled ($toggleslash)

            · Ranking: enabled ($toggleclaimrank/$togglelikerank)
            · Ranks displayed during rolls: claims only ($togglerolls)
            · NSFW series: **disabled** ($togglensfw)
            · Disturbing imagery series: enabled ($toggledisturbing)
            · Child characters: enabled ($togglechildtag)
            · Rolls sniping: **2** ($togglesnipe) => **8** sec.
            · Kakera sniping: **1** ($togglekakerasnipe) => **8** sec.
            · Limit of characters per harem: **8100** ($haremlimit)
            · Reacts: ****for all your rolls**** ($togglereact)
            · Custom reactions: yes ($claimreact list)
            · Kakera reactions more recognizable: no ($kakerareact switchset)

            · Kakera trading: **disabled** ($togglekakeratrade)
            · Kakera calculation: claim and like ranks (and number of claimed characters) ($togglekakeraclaim/$togglekakeralike)
            · Kakera value displayed during rolls: enabled ($togglekakerarolls)
            · $kakeraloot wishprotect: enabled ($togglewishprotect)"""

def get_wait(text):
    waits = wait_finder.findall(text)
    if len(waits):
        hours = int(waits[0][0]) if waits[0][0] != '' else 0
        return (hours*60+int(waits[0][1]))*60
    return 0
def get_pwait(text):
    waits = poke_finder.findall(text)
    if len(waits):
        hours = int(waits[0][0]) if waits[0][0] != '' else 0
        return (hours*60+int(waits[0][1]))*60
    return 0

def parse_settings_message(message):
    if message == None:
        return None
    val_parse = re.compile(r'\*\*(\S+)\*\*').findall
    num_parse = re.compile(r'(\d+)').findall
    num_parsedec = re.compile(r'(\d*[.,]?\d+)').findall

    settings_p = re.findall(r'\w+: (.*)',message)
    settings = dict()

    settings['prefix'] = val_parse(settings_p[0])[0]
    settings['prefix_len'] = len(settings['prefix'])
    settings['claim_reset'] = int(num_parse(settings_p[2])[0]) # in minutes
    settings['reset_min'] = int(num_parse(settings_p[3])[0])
    settings['shift'] = int(num_parse(settings_p[4])[0])
    settings['max_rolls'] = int(num_parse(settings_p[5])[0])
    settings['expiry'] = float(num_parse(settings_p[6])[0])
    settings['claim_snipe'] = [float(v) for v in num_parsedec(settings_p[17])]
    settings['kak_snipe'] = [float(v) for v in num_parsedec(settings_p[18])]


    settings['claim_snipe'][0] = int(settings['claim_snipe'][0])
    # pad out claim/kak snipe for default '0 second cooldown'
    if len(settings['claim_snipe']) < 2:
        settings['claim_snipe'] += [0.0]
    if len(settings['kak_snipe']) < 2:
        settings['kak_snipe'] += [0.0]
    settings['claim_snipe'][0] = int(settings['claim_snipe'][0])
    settings['kak_snipe'][0] = int(settings['kak_snipe'][0])

    settings['pending'] = None
    settings['rolls'] = 0
 
    return settings

def get_snipe_time(channel,rolled,message,botter):
    # Returns delay for when you are able to snipe a given roll
    r,d = channel_settings[channel]['claim_snipe']
    if r == 0:
        # Anarchy FTW!
        return 0.0

    global user

    is_roller = (rolled == botter.user.id)
    print(is_roller)

    if (r < 4 or r == 5) and is_roller:
        # Roller can insta-snipe
        return 0.0
    if r == 2 and not is_roller:
        # Not the roller.
        return d

    wished_for = mention_finder.findall(message)

    # Wish-based rules
    if not len(wished_for):
        # Not a WISHED character
        if r > 4:
            # Combined restriction, roller still gets first dibs
            return 0.0 if is_roller else d
        return 0.0

    if r > 2 and user['id'] in wished_for:
        # Wishers can insta-snipe
        return 0.0

    if r == 1 and rolled not in wished_for:
        # Roller (who is not us) did not wish for char, so can insta-snipe
        return 0.0

    return d

    wished_for = mention_finder.findall(message)

    # Wish-based rules
    if not len(wished_for):
        # Not a WISHED character
        if r > 4:
            # Combined restriction, roller still gets first dibs
            return 0.0 if is_roller else d
        return 0.0

    if r > 2 and user['id'] in wished_for:
        # Wishers can insta-snipe
        return 0.0

    if r == 1 and rolled not in wished_for:
        # Roller (who is not us) did not wish for char, so can insta-snipe
        return 0.0

    return d


def snipe(recv_time,snipe_delay):
    if snipe_delay != 0.0:
        try:
            time.sleep((recv_time+snipe_delay)-time.time())
        except ValueError:
            # sleep was negative, so we're overdue!
            return
    time.sleep(.5)

def is_rolled_char(m):
    # Check if message has embeds
    if not m.embeds:
        return False

    # Convert the first embed to a dictionary
    embed = m.embeds[0].to_dict()

    # Check if the embed contains the necessary keys
    if "image" not in embed or "author" not in embed or list(embed.get("author", {}).keys()) != ['name']:
        # Not a valid roll if no image or author or if author keys don't match
        return False

    # Check if there's a footer with pagination, which would indicate it's not a roll
    if "footer" in embed and "text" in embed["footer"]:
        if pagination_finder.findall(embed["footer"]["text"]):
            # Pagination found, not a roll
            return False

    # All checks passed, it seems to be a valid roll
    return True

class MyClient(discord.Client):

    async def bg_task(self,taskid):
        rollingchannel = self.get_channel(taskid)
        wait = 0
        retries = 0
        c_settings = channel_settings[taskid]
        roll_cmd = c_settings['prefix'] + roll_prefix
        def msg_check(message):
            return message.author.id == mudae and message.channel.id == taskid

        def quiet_channel_check(message):
            return message.channel.id == taskid and message.author.bot is False

        while True:

            # Wait for a quiet Moment
            try:
                print(f"Checking if channel is quiet...")
                await self.wait_for('message',timeout=60.0,check=quiet_channel_check)
                print(f"Activity Detected in channel {taskid} from users. delaying rolls")
                continue
            except asyncio.TimeoutError:
                print(f"No user Activity in channel {taskid} proceeding rolls")
            # Rolling Process     
            while wait == 0:
                wait_for_mudae = self.loop.create_task(self.wait_for('message',timeout=10.0,check=msg_check))
                await asyncio.sleep(2)
                await rollingchannel.send(roll_cmd)
                try:
                    msg = await wait_for_mudae
                    if msg.content.startswith(f"**{self.user.name}"):

                        wait = get_wait(msg.content)
                        print(wait)
                        retries = 0

                except asyncio.TimeoutError:
                    retries += 1
                    print(f"Timeout no Response Retrying attempt {retries} max: 5 in 60 sec ")
                    if retries >= 5:
                        print(f"The Automated rolling on channelid {taskid} is ded. Requires Restart of the program")
                        return
                    await asyncio.sleep(60)
            await asyncio.sleep(wait)
            wait = 0


    async def on_ready(self):
        print(f'Logged on as {self.user}!')

        for xchan in mhids:
            loochannel = self.get_channel(xchan)
            print(loochannel)
            loohistory = await discord.utils.find(lambda m: m.author.id == mudae and "togglensfw" in m.content, loochannel.history(limit=100))
            print(loohistory)
            if loohistory != None:
                looc_settings = parse_settings_message(loohistory.content)
            else:
                looc_settings = parse_settings_message(default_settings_if_no_settings)
            channel_settings[xchan] = looc_settings

        channel = self.get_channel(xchan)
        historyc = await discord.utils.find(lambda m: m.author.id == mudae and "togglensfw" in m.content, channel.history(limit=None))
        print(parse_settings_message(historyc.content))
        c_settings = parse_settings_message(historyc.content)
        dc_settings = parse_settings_message(default_settings_if_no_settings)
        channel_settings[123] = dc_settings
        channel_settings[xchan] = c_settings

        print(channel_settings)
        #self.loop.create_task(self.bg_task(807061315792928948))





    async def on_message(self, message):
        recv=time.time()
        #Don't Message Self
        if message.author == self.user:
            pass

        #We don't Have settings in the channel_settings so Skip
        if int(message.channel.id) not in channel_settings:
            return

        c_settings = channel_settings[message.channel.id]

        if c_settings['pending'] is None and message.author.id != mudae and message.content[0:c_settings['prefix_len']] == c_settings['prefix'] and message.content.split(' ')[0][c_settings['prefix_len']:] in mudae_cmds:
            c_settings['pending'] = message.author.id
            return

        #Interact with Mudae only
        if message.author.id == mudae:


            if message.interaction is None:
                ineractio = c_settings['pending']
            else:
                ineractio = message.interaction.user.id
            c_settings['pending'] = None

            msg_buf[message.id] = {'claimed':(int(message.embeds[0].color) if message.embeds else None) not in (16751916,1360437),'rolled':ineractio == int(message.author.id)}

            print(f"Our user rolled in {message.channel}" if ineractio == self.user.id else f"Someone else rolled in {message.channel}")

            if message.embeds != []:
                #Set up Snipe Delay
                try:
                    snipe_delay = get_snipe_time(message.channel.id,ineractio,message.content,self)
                except KeyError:
                    snipe_delay = get_snipe_time(123,ineractio,message.content,self)

                if not is_rolled_char(message):
                    pass

                #Set up Claim Delay
                if claimdelayjson <= snipe_delay:
                    claim_delay = snipe_delay
                else:
                    claim_delay = claimdelayjson
                #print(f'Charcter claim delay: {claim_delay} seconds')

                #Set up Kakera Delay
                if kakdelayjson <= snipe_delay:
                    kakera_delay = snipe_delay
                else:
                    kakera_delay = kakdelayjson
                #print(f'Kakera claim delay: {kakera_delay} seconds')
             
                objects = message.embeds[0].to_dict()

                #Set up Charname
                if 'author' in objects.keys():
                    charname = objects['author']['name']
                else:
                    charname = "jkqemnxcv not found"

                #Wish sniping
                if str(self.user.id) in message.content or "Wished" in message.content:
                    print(f"Wished {objects['author']['name']} in {message.channel.id}: {message.channel.name} ")
                    emoji = use_emoji
                    snipe(recv,snipe_delay)
                    if message.components == []:
                        if message.reactions != [] and not message.reactions[0].custom_emoji:
                            emoji = message.reactions[0].emoji
                            await message.add_reaction(emoji)
                            logger.info(f"Reaction added on {charname} ")
                    else:
                        await message.components[0].children[0].click()
                        logger.info(f"Button Clicked on {charname}")

                #Series Sniping
                for ser in series_list:
                    if ser in objects['description'] and objects['color'] == 16751916:
                        print(f"Attempting to Claim {objects['author']['name']} from {ser} in ({message.channel.id}):{message.channel.name}")
                        emoji = use_emoji
                        snipe(recv,claim_delay)
                        if message.components == []:
                            if message.reactions != [] and not message.reactions[0].custom_emoji:
                                emoji = message.reactions[0].emoji
                            await message.add_reaction(emoji)
                            break
                        else:
                            await message.components[0].children[0].click()
                            break

                #Character Sniping
                if charname.lower() in chars:
                    logger.info(f"Character Claim {charname}")
                    emoji = use_emoji
                    snipe(recv,claim_delay)
                    if message.components == []:
                        if message.reactions != [] and not message.reactions[0].custom_emoji:
                            emoji = message.reactions[0].emoji
                            await message.add_reaction(emoji)
                    else:
                        await message.components[0].children[0].click()

                #Kakera Sniping
                if message.components != [] and "kakera" in message.components[0].children[0].emoji.name:

                    if "kakeraP" in message.components[0].children[0].emoji.name:
                        snipe(recv,kakera_delay)
                        await message.components[0].children[0].click()

                    cooldown = kakera_wall.get(message.guild.id,0) - time.time()

                    if cooldown <= 1:
                        logger.info(f" {message.components[0].children[0].emoji.name} found in: {message.guild.id} awaiting {kakera_delay}")
                        snipe(recv,kakera_delay)
                        await message.components[0].children[0].click()
                    else:
                        logger.info(f" Skipped {message.components[0].children[0].emoji.name} Skipped in: {message.guild.id}")

                    def kak_check(m):
                        return m.author.id == mudae and m.guild.id == message.guild.id

                    wait_for_kak = self.loop.create_task(self.wait_for('message',timeout=10.0,check=kak_check))
                    try:
                        msgk = await wait_for_kak
                        print(msgk)

                        if msgk.content.startswith(f"**{self.user.name}"):
                            time_to_kak = waitk_finder.findall(msgk.content)
                        else:
                            time_to_kak = []
                        print(time_to_kak)

                    except asyncio.TimeoutError:
                        time_to_kak = []

                    if len(time_to_kak):
                        timegetk = (int(time_to_kak[0][0] or "0")*60+int(time_to_kak[0][1] or "0"))*60
                        logger.info(f"{timegetk} set for server {message.guild.id}")
                        kakera_wall[message.guild.id] = timegetk + time.time()

client = MyClient()
client.run(settings['token'])
