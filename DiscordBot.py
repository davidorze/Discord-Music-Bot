import os
import sys
import codecs
import discord
from discord.ext import commands
from discord.ext import tasks
#import discord_components
import youtube_dl
from collections import defaultdict
from pprint import pprint
import asyncio
import datetime
import time
import math
import re
import SettingEnvVar
from random import random
#import spotipy
#from spotipy.oauth2 import SpotifyClientCredentials
import lyricsgenius as lg

intents = discord.Intents.default()
intents.members = True
botToken = os.getenv('BOT_TOKEN')

#auth_manager = SpotifyClientCredentials()
#sp = spotipy.Spotify(auth_manager=auth_manager)
#track = sp.track('https://open.spotify.com/track/6sH0zEauzk2ih4kGWQliQL?si=da7682a0355c47ec')
#pprint(track)

genius = lg.Genius('GENIUS_TOKEN', skip_non_songs=True, excluded_terms=["(Remix)", "(Live)"], remove_section_headers=True)
client = commands.Bot(command_prefix='\\', case_insensitive=True, intents=intents)
queues = defaultdict(list)
infos = defaultdict(list)
tempoSong = {}
start = {}
notPlaying = 0



@client.command(aliases=['tp'], hidden=True)
async def testplay(ctx, *, url: str):
    global infos
    global queues
    id = ctx.guild.id
    userID = ctx.author.id    
    ydl_opts = {'format': 'best', 'default_search': 'ytsearch1', 'ignoreerrors': True}
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        video = ydl.extract_info(url, download=False)
    name = video['entries'][0]['track']
    url = video['entries'][0]['formats'][0]['url']
    voice = discord.utils.get(client.voice_clients, guild=ctx.guild)
    if (voice == None):
        await ctx.author.voice.channel.connect()
        voice = discord.utils.get(client.voice_clients, guild=ctx.guild)

    await ctx.channel.send(name + ' está tocando!')
    FFMPEG_OPTS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}
    voice.play(discord.FFmpegPCMAudio(url, **FFMPEG_OPTS), after=lambda e: start_playing(canal, id , voice, ctx))



#def check_queue(canal, id, voice):
#    if queues[id] != []:
#        start_playing(id, voice)

def parse_duration(duration: int):
    minutes, seconds = divmod(duration, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)

    duration = []
    if days > 0:
        duration.append('{} days'.format(days))
    if hours > 0:
        duration.append('{} hours'.format(hours))
    if minutes > 0:
        duration.append('{} minutes'.format(minutes))
    if seconds > 0:
        duration.append('{} seconds'.format(seconds))
    i = 0
    for n in duration:
        if (i == 0 and n[-5:] == 'hours' and int(n[:2]) < 10): tempo = n[:1]
        elif (i == 0 and int(n[:2]) < 10): tempo = n[:1]
        elif (i == 0): tempo = n[:2]
        elif (int(n[:2]) < 10): tempo += ':0' + n[:2]
        else: tempo += ':' + n[:2]
        i += 1
            
    return tempo

@client.command(aliases=['j'], description='Faz o bot entrar em seu canal de voz atual')
async def join(ctx):
    #try: await ctx.message.delete()
    try:
        channel = ctx.author.voice.channel
        print(channel)
        await channel.connect()
        checkIfAlone.start(ctx)
    except:
        if (discord.utils.get(client.voice_clients, guild=ctx.guild).is_playing()): await ctx.channel.send('O Bot já está conectado no canal ' + str(discord.utils.get(client.voice_clients, guild=ctx.guild).channel.name) + '!')
        else: await ctx.channel.send('Você não está conectado em nenhum canal de voz! Conecte-se e tente novamente.')
    #channel = discord.utils.get(ctx.guild.voice_channels, name='geral')
    
        
@client.command(aliases=['pl', 'p'])
async def play(ctx, *, url: str):
    global infos
    global queues
    id = ctx.guild.id
    userID = ctx.author.id
    ydl_opts = {'format': 'best', 'default_search': 'ytsearch1', 'ignoreerrors': True, 'playlist_items':'1'}
    async with ctx.channel.typing():
     with youtube_dl.YoutubeDL(ydl_opts) as ydl:
         video = ydl.extract_info(url, download=False)
         #original_stdout = sys.stdout # Save a reference to the original standard output
         #with open('output2.txt', 'wb') as f:
         #    sys.stdout = f
         #    sys.stdout = codecs.getwriter('utf8')(sys.stdout) # Change the standard output to the file we created.
         #    pprint(video)
         #    sys.stdout = original_stdout # Reset the standard output to its original value
         #pprint(video)
         create_playlist(video, id, userID, False)
     voice = discord.utils.get(client.voice_clients, guild=ctx.guild)
    if (voice == None):
        await join(ctx)
        voice = discord.utils.get(client.voice_clients, guild=ctx.guild)
    try:
        if not voice.is_playing():
            #print('not playing')
            if voice.is_paused(): await resume(ctx)
            else:
                #print('call')
                await call_play(ctx.channel, id, voice, ctx)
                await ctx.channel.send(infos[id][0]['song'] + ' está tocando!')
        elif voice.is_playing():
            j = len(infos[id])-1
            await ctx.channel.send(infos[id][j]['song'] + ' adicionada na fila!')
    except:
        await ctx.channel.send('Algo deu errado, por favor, tente novamente!', delete_after=60)
    if '_type' in video:
        ydl_opts = {'format': 'best', 'default_search': 'ytsearch1', 'ignoreerrors': True}
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            video = ydl.extract_info(url, download=False)
            create_playlist(video, id, userID, False)
            await remove(ctx, 1, True)


@client.command(aliases=['s'])
async def search(ctx, *, url: str):
    global infos
    global queues
    id = ctx.guild.id
    voice = discord.utils.get(client.voice_clients, guild=ctx.guild)
    userID = ctx.author.id
    if (voice == None):
        await join(ctx)
        voice = discord.utils.get(client.voice_clients, guild=ctx.guild)
    ydl_opts = {'format': 'best', 'default_search': 'ytsearch10', 'ignoreerrors': True}
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        video = ydl.extract_info(url, download=False)
    if '_type' in video and len(video['entries']) == 10:
        await askAfterSearch(video, id, userID, ctx)
    try:
         if not voice.is_playing():
             #print('not playing')
             if voice.is_paused(): await resume(ctx)
             else:
                 #print('call')
                 await call_play(ctx.channel, id, voice, ctx)
                 await ctx.channel.send(infos[id][0]['song'] + ' está tocando!')
         elif voice.is_playing():
             j = len(infos[id])-1
             await ctx.channel.send(infos[id][j]['song'] + ' adicionada na fila!')
    except:
         await ctx.channel.send('Algo deu errado, por favor, tente novamente!', delete_after=60)

def create_playlist(video, id, userID, isPlayNow):
    global infos
    global queues
    info = {}
    if '_type' in video:
        print('playlist')
        i = 0
        for ent in video['entries']:
            info[i] = (ent['formats'][0])
            info[i].update({'duration': ent['duration'], 'id': ent['id']})
            try: info[i].update({'title': ent['track']})
            except: 
                if any('artist' in ele for ele in ent): info[i].update({'title': ent['title'].replace(ent['artist'], '')})
                else: info[i].update({'title': ent['title']})
            try: 
                artists = re.sub("[^\w' ]", "", ent['artist']).split("  ")
                pprint(artists[0])
                info[i].update({'artist': artists[0]})
            except: info[i].update({'artist': ''})
            i += 1
    elif 'entries' in video:
        print('pesquisa')
        i = 0
        for ent in video['entries']:
            info[i] = (ent['formats'][0])
            info[i].update({'duration': ent['duration'], 'id': ent['id']})
            try: info[i].update({'title': ent['track']})
            except:
                if any('artist' in ele for ele in ent): info[i].update({'title': ent['title'].replace(ent['artist'], '')})
                else: info[i].update({'title': ent['title']})
            try:
                artists = re.sub("[^\w' ]", "", ent['artist']).split("  ")
                pprint(artists[0])
                info[i].update({'artist': artists[0]})
            except: info[i].update({'artist': ''})
            i += 1
    elif 'formats' in video:
        print('link')
        pprint(video)
        info[0] = video['formats'][0]
        print('fez info00')
        info[0].update({'duration': video['duration'], 'id': video['id']})
        print('fez info01')
        try:
            artists = re.sub("[^\w' ]", "", ent['artist']).split("  ")
            pprint(artists)
            info[0].update({'artist': artists[0]})
        except: 
            info[0].update({'artist': ''})
            print('n tem artist')
        try: 
            info[0].update({'title': video['track']})
            print('tem track')
        except:
           print('n tem track')
           if any('artist' in ele for ele in video): info[0].update({'title': video['title'].replace(video['artist'], '')})
           else: info[0].update({'title': video['title']})
    elif 'uploader' in video:
        print('testando not YT')
        info[0] = video
    print('goingToAppend')
    appendToList(info, id, userID, isPlayNow)

def appendToList(info, id, userID, isPlayNow):
    global infos
    global queues
    i = 0
    if isPlayNow:
        while i < len(info):
            queues[id].insert(0, info[i]['url'])
            try: 
                tempo = parse_duration(info[i]['duration'])
                infos[id].insert(1, {'user': ('<@!'+str(userID)+'>'), 'song': info[i]['title'], 'duration': tempo, 'songId': info[i]['id'], 'url': info[i]['url'], 'artist': info[i]['artist']})
            except:
                tempo = '∞'
                infos[id].insert(1, {'user': ('<@!'+str(userID)+'>'), 'song': info[i]['title'][:-17], 'duration': tempo, 'songId': info[i]['id'], 'url': info[i]['url'], 'artist': info[i]['artist']}) 
            i += 1
    else:
        while i < len(info):
            queues[id].append(info[i]['url'])
            try: 
                tempo = parse_duration(info[i]['duration'])
                infos[id].append({'user': ('<@!'+str(userID)+'>'), 'song': info[i]['title'], 'duration': tempo, 'songId': info[i]['id'], 'url': info[i]['url'], 'artist': info[i]['artist']})
            except:
                tempo = '∞'
                infos[id].append({'user': ('<@!'+str(userID)+'>'), 'song': info[i]['title'][:-17], 'duration': tempo, 'songId': info[i]['id'], 'url': info[i]['url'], 'artist': info[i]['artist']}) 
            i += 1


async def askAfterSearch(video, id, userID, ctx):
    embed=discord.Embed(description="Essas são as músicas encontradas pela sua pesquisa, digite o número da que deseja:", color=0x7cb84f)
    if len(video['entries'])==0: embed=discord.Embed(title="Não achou nada!", description="Use o comando \'play\' para adicionar músicas!", color=0x7cb84f)
    else:
        i = 1
        for song in video['entries']:
            try: 
                tempo = parse_duration(song['duration'])
                embed.add_field(name=str(i) + ' - ' + song['title'], value=('Duração: ' + tempo), inline=False)
            except:
                tempo = '∞'
                if song['title'] is not None: embed.add_field(name=str(i) + ' - ' + song['title'][:-17], value=('Duração: ' + tempo), inline=False)
            i += 1
    await ctx.channel.send(embed=embed, delete_after=120)
    def check(m):
        return (m.content == '1' or '2' or '3' or '4' or '5' or '6' or '7' or '8' or '9' or '10') and m.channel == ctx.channel and m.author == ctx.author
    try:
        msg = await client.wait_for('message', check=check, timeout=120)
    except:
        await ctx.channel.send('Nenhuma música foi selecionada!', delete_after=60)
    video = video['entries'][int(msg.content)-1]
    create_playlist(video, id, userID, False)

def start_playing(canal, id, voice, ctx):
    global infos
    global queues
    FFMPEG_OPTS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}
    if (0 < len(queues[id])):
        try:
            start[id] = time.time()
            voice.play(discord.FFmpegPCMAudio(queues[id].pop(0), **FFMPEG_OPTS), after=lambda e: start_playing(canal, id , voice, ctx))
            if (len(queues[id])+2==(len(infos[id]))): infos[id].pop(0)
        except:
            pass
    else:
        #loop = asyncio.new_event_loop()
        #asyncio.set_event_loop(loop)
        #loop.run_until_complete(queue(ctx))
        if len(infos[id]) > 0: infos[id].pop(0)

async def call_play(canal, id, voice, ctx):
    global infos
    global queues
    #FFMPEG_OPTS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}
    start_playing(canal, id, voice, ctx)
    #await canal.send('Fila terminou, adicione mais músicas!')

@client.command(aliases=['next', 'sk'])
async def skip(ctx):
    voice = discord.utils.get(client.voice_clients, guild=ctx.guild)
    id = ctx.guild.id
    voice.stop()

@client.command(aliases=['pn', 'playn'])
async def playnow(ctx, *, url: str):
    global infos
    global queues
    id = ctx.guild.id
    userID = ctx.author.id
    ydl_opts = {'format': 'best', 'default_search': 'ytsearch1', 'ignoreerrors': True}
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        video = ydl.extract_info(url, download=False)
    create_playlist(video, id, userID, True)
    voice = discord.utils.get(client.voice_clients, guild=ctx.guild)
    if (voice == None):
        await join(ctx)
        voice = discord.utils.get(client.voice_clients, guild=ctx.guild)
    if not voice.is_playing():
        if voice.is_paused(): await resume(ctx)
        else:
            await call_play(ctx.channel, id, voice, ctx)
            await ctx.channel.send(infos[id][1]['song'] + ' está tocando!')
    elif voice.is_playing():
        #voice.stop()
        await ctx.channel.send(infos[id][1]['song'] + ' foi adicionada como próxima da fila!')
   
@client.command(aliases=['q', 'fila'])
async def queue(ctx):
    global infos
    global queues
    id = ctx.guild.id
    try: await ctx.message.delete()
    except: None
    async with ctx.channel.typing():
        embed=discord.Embed(title="Fila", description="Essas são as próximas músicas a tocar:", color=0x7cb84f)
        try:
           tempoSong[id] = round(time.time() - start[id])
        except:
            tempoSong[id] = 0
            #print('Ainda não tocou nada')
        i = 0
        if len(infos[id])==0: embed=discord.Embed(title="A Fila está vazia!", description="Use o comando \'play\' para adicionar mais músicas!", color=0x7cb84f)
        else:
            for song in infos[id]:
                if (i == 0) and song['artist'] != '': embed.add_field(name='Agora tocando:\n' + song['song'] + ' - ' + song['artist'] + '\nDuração: ' + str(datetime.timedelta(seconds=tempoSong[id])) + '/' + song['duration'], value=('Adicionado por: ' + song['user']), inline=False)
                elif (i > 0) and song['artist'] != '': embed.add_field(name=str(i) + ' - ' + song['song'] + ' - ' + song['artist'] + '\nDuração: ' + song['duration'], value=('Adicionado por: ' + song['user']), inline=False)
                elif (i == 0) and song['artist'] == '': embed.add_field(name='Agora tocando:\n' + song['song'] + '\nDuração: ' + str(datetime.timedelta(seconds=tempoSong[id])) + '/' + song['duration'], value=('Adicionado por: ' + song['user']), inline=False)
                elif (i > 0) and song['artist'] == '': embed.add_field(name=str(i) + ' - ' + song['song'] + '\nDuração: ' + song['duration'], value=('Adicionado por: ' + song['user']), inline=False)
                i += 1
        try:
            await ctx.channel.send(embed=embed)
        except:
            await ctx.channel.send(embed=embed)

@client.command(aliases=['l', 'sair'])
async def leave(ctx):
    voice = discord.utils.get(client.voice_clients, guild=ctx.guild)
    try:
        await voice.disconnect()
        checkIfAlone.cancel()
    except:
        await ctx.channel.send('O Bot não está conectado em nenhum canal do servidor!')

@client.command()
async def pause(ctx):
    voice = discord.utils.get(client.voice_clients, guild=ctx.guild)
    try:
        await voice.pause()
        await ctx.channel.send('Pausando!')
    except:
        await ctx.channel.send('O Bot não está conectado em nenhum canal do servidor!')

@client.command(aliases=['r'])
async def resume(ctx):
    global infos
    id = ctx.guild.id
    voice = discord.utils.get(client.voice_clients, guild=ctx.guild)
    try:
        await voice.resume()
        await ctx.channel.send('Resumindo: ' + str(infos[id][0]['song']))
    except:
        await ctx.channel.send('O Bot não está com tocando nada!')

@client.command()
async def remove(ctx, item: int, isDuplicate=False):
    global infos
    global queues
    id = ctx.guild.id
    if len(infos[id]) > item > 0:
        try:
            queues[id].pop(item-1)
            if(not isDuplicate): await ctx.channel.send('Removendo música ' + str(infos[id].pop(item)['song']) + ' da lista!')
        except:
            if(not isDuplicate): await ctx.channel.send('O Bot não tem nada na fila!')
    else:
        if(not isDuplicate): await ctx.channel.send('Escreva um número dentro da fila!')

@client.command(aliases=['parar'])
async def stop(ctx):
    global infos
    global queues
    id = ctx.guild.id
    queues[id].clear()
    voice = discord.utils.get(client.voice_clients, guild=ctx.guild)
    try:
        voice.stop()
        await ctx.channel.send('Parando de tocar!')
    except:
        await ctx.channel.send('O Bot não está tocando nada!')
    infos[id].clear()
    tempoSong[id] = None
    start[id] = None

@client.command(aliases=['random'])
async def shuffle(ctx):
    global infos
    global queues
    id = ctx.guild.id
    temp0i = infos[id].pop(0)
    for i in range(n):
        k = i + (int(random() * (n - i))) #random.Next(n);
        temp = queues[id][k]
        queues[id][k] = queues[id][i]
        queues[id][i] = temp
        tempInfo = infos[id][k]
        infos[id][k] = infos[id][i]
        infos[id][i] = tempInfo
    infos[id].insert(0, temp0i)

@client.command(aliases=['lyric', 'letra', 'letras'])
async def lyrics(ctx):
    global infos
    id = ctx.guild.id
    song = genius.search_song(infos[id][0]['song'], infos[id][0]['artist'])
    await ctx.channel.send(song.lyrics)


#@client.command()
#async def purge(ctx):
#    for file in os.listdir("./songs/"):
#        os.remove("songs/"+file)
#    await ctx.channel.send('O Bot apagou todas as músicas baixadas!')

@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))
    
    #checking = asyncio.new_event_loop()
    #asyncio.run_coroutine_threadsafe(checkIfAlone())

#@client.event
#async def on_message(message):
#  if message.content.startswith('$hi'):
#    await message.channel.send('Hello!')
#    await join(message)

#async def on_voice_state_update(member, before, after):
#    global notPlaying
#    print('Update')
    
#    voice = member.guild.voice_client
#    if voice is None:
#        # Exiting if the bot it's not connected to a voice channel
#        return 
#    if not voice.is_playing() and notPlaying == 10:
#       notPlaying = 0
#       await leave(ctx)
#    if len(voice.channel.members) == 19821:
#       await leave(ctx)

@tasks.loop(seconds = 60)
async def checkIfAlone(ctx):
    global notPlaying    
    try:
        voice = discord.utils.get(client.voice_clients, guild=ctx.guild)
        member_count = len(voice.channel.voice_states.keys())
        for user in voice.channel.voice_states.keys():
            isBot = client.get_user(user)
            if isBot.bot: member_count -= 1
        if member_count == 0:
            await leave(ctx)
            await ctx.channel.send('Estou sozinho, vou embora! T_T')
        elif not voice.is_playing():
            notPlaying += 1
            if notPlaying == 3:
                await leave(ctx)
                await ctx.channel.send('Se quiser ouvir algo, é só chamar de volta!')
                notPlaying = 0
        else:
            notPlaying = 0
    except:
        None


@client.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        msg = ctx.message.content
        if msg == '\\p':
            if not voice.is_playing(): 
                if voice.is_paused(): await resume(ctx)
                else: ctx.channel.send('Não se esqueça de colocar a música ou a URL!')
        elif msg == '\\letra' or '\\letras' or '\\lyric' or '\\lyrics':
            global infos
            id = ctx.guild.id
            song = genius.search_song(infos[id][0]['song'], infos[id][0]['artist'])
            await ctx.channel.send(song.lyrics)

client.run(botToken)
