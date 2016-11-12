from datetime import datetime,timedelta
from rpc import RPC
from xbmcswift2 import Plugin
from xbmcswift2 import actions
import HTMLParser
import os
import random
import re
import requests
import sqlite3
import time
import xbmc,xbmcaddon,xbmcvfs,xbmcgui
import xbmcplugin
import json

from types import *

plugin = Plugin()
big_list_view = False


def addon_id():
    return xbmcaddon.Addon().getAddonInfo('id')

def log(v):
    xbmc.log(repr(v))

def get_icon_path(icon_name):
    if plugin.get_setting('user.icons') == "true":
        user_icon = "special://profile/addon_data/%s/icons/%s.png" % (addon_id(),icon_name)
        if xbmcvfs.exists(user_icon):
            return user_icon
    return "special://home/addons/%s/resources/img/%s.png" % (addon_id(),icon_name)

def remove_formatting(label):
    label = re.sub(r"\[/?[BI]\]",'',label)
    label = re.sub(r"\[/?COLOR.*?\]",'',label)
    return label

def escape( str ):
    str = str.replace("&", "&amp;")
    str = str.replace("<", "&lt;")
    str = str.replace(">", "&gt;")
    str = str.replace("\"", "&quot;")
    return str

def unescape( str ):
    str = str.replace("&lt;","<")
    str = str.replace("&gt;",">")
    str = str.replace("&quot;","\"")
    str = str.replace("&amp;","&")
    return str

@plugin.route('/play/<url>')
def play(url):
    xbmc.executebuiltin('PlayMedia("%s")' % url)

@plugin.route('/execute/<url>')
def execute(url):
    xbmc.executebuiltin(url)

@plugin.route('/add_favourite/<favourites_file>/<name>/<url>/<thumbnail>')
def add_favourite(favourites_file,name,url,thumbnail):
    f = xbmcvfs.File(favourites_file,"rb")
    data = f.read()
    f.close()
    if not data:
        data = '<favourites>\n</favourites>'
    fav = '    <favourite name="%s" thumb="%s">%s</favourite>\n</favourites>' % (name,thumbnail,url)
    data = data.replace('</favourites>',fav)
    f = xbmcvfs.File(favourites_file,"wb")
    f.write(data)
    f.close()
    xbmc.executebuiltin('Container.Refresh')

@plugin.route('/favourites/<favourites_file>/<name>/<url>')
def remove_favourite(favourites_file,name,url):
    f = xbmcvfs.File(favourites_file,"rb")
    data = f.read()
    f.close()
    data = re.sub('.*<favourite name="%s".*?>%s</favourite>.*\n' % (re.escape(name),re.escape(url)),'',data)
    f = xbmcvfs.File(favourites_file,"wb")
    f.write(data)
    f.close()
    xbmc.executebuiltin('Container.Refresh')

@plugin.route('/rename_favourite/<favourites_file>/<name>/<fav>')
def rename_favourite(favourites_file,name,fav):
    d = xbmcgui.Dialog()
    dialog_name = unescape(name)
    new_name = d.input("New Name for: %s" % dialog_name,dialog_name)
    if not new_name:
        return
    f = xbmcvfs.File(favourites_file,"rb")
    data = f.read()
    f.close()
    new_fav = fav.replace(name,escape(new_name))
    data = data.replace(fav,new_fav)
    f = xbmcvfs.File(favourites_file,"wb")
    f.write(data)
    f.close()
    xbmc.executebuiltin('Container.Refresh')

@plugin.route('/change_favourite_thumbnail/<favourites_file>/<thumbnail>/<fav>')
def change_favourite_thumbnail(favourites_file,thumbnail,fav):
    d = xbmcgui.Dialog()
    new_thumbnail = d.browse(2, 'Choose Image', 'files')
    if not new_thumbnail:
        return
    f = xbmcvfs.File(favourites_file,"rb")
    data = f.read()
    f.close()
    new_fav = fav.replace(thumbnail,escape(new_thumbnail))
    data = data.replace(fav,new_fav)
    f = xbmcvfs.File(favourites_file,"wb")
    f.write(data)
    f.close()
    xbmc.executebuiltin('Container.Refresh')

@plugin.route('/favourites/<folder_path>')
def favourites(folder_path):
    items = []
    favourites_file = "%sfavourites.xml" % folder_path
    f = xbmcvfs.File(favourites_file,"rb")
    data = f.read()
    favourites = re.findall("<favourite.*?</favourite>",data)
    for fav in favourites:
        url = ''
        match = re.search('<favourite name="(.*?)" thumb="(.*?)">(.*?)<',fav)
        if match:
            label = match.group(1)
            thumbnail = match.group(2)
            url = match.group(3)
        else:
            match = re.search('<favourite name="(.*?)">(.*?)<',fav)
            if match:
                label = match.group(1)
                thumbnail = get_icon_path('unknown')
                url = match.group(2)
        if url:
            context_items = []
            context_items.append(("[COLOR yellow][B]%s[/B][/COLOR] " % 'Remove', 'XBMC.RunPlugin(%s)' % (plugin.url_for(remove_favourite, favourites_file=favourites_file, name=label, url=url))))
            context_items.append(("[COLOR yellow][B]%s[/B][/COLOR] " % 'Rename', 'XBMC.RunPlugin(%s)' % (plugin.url_for(rename_favourite, favourites_file=favourites_file, name=label, fav=fav))))
            context_items.append(("[COLOR yellow][B]%s[/B][/COLOR] " % 'Change Image', 'XBMC.RunPlugin(%s)' % (plugin.url_for(change_favourite_thumbnail, favourites_file=favourites_file, thumbnail=thumbnail, fav=fav))))
            items.append(
            {
                'label': unescape(label),
                'path': plugin.url_for('execute',url=unescape(url)),
                #'path': plugin.url_for('play',url=unescape(url)),
                'thumbnail':unescape(thumbnail),
                'context_menu': context_items,
            })
    return items


@plugin.route('/add_item/<title>/<path>/icon')
def add_item(title,path,icon):
    pass

@plugin.route('/add_favourites/<path>')
def add_favourites(path):
    items = []
    kodi_favourites = "special://profile/favourites.xml"
    output_file = "%sfavourites.xml" % path
    f = xbmcvfs.File(kodi_favourites,"rb")
    data = f.read()
    favourites = re.findall("<favourite.*?</favourite>",data)
    for fav in favourites:
        url = ''
        match = re.search('<favourite name="(.*?)" thumb="(.*?)">(.*?)<',fav)
        if match:
            label = match.group(1)
            thumbnail = match.group(2)
            url = match.group(3)
        else:
            match = re.search('<favourite name="(.*?)">(.*?)<',fav)
            if match:
                label = match.group(1)
                thumbnail = get_icon_path('unknown')
                url = match.group(2)
        if url:
            context_items = []
            context_items.append(("[COLOR yellow][B]%s[/B][/COLOR] " % 'Add', 'XBMC.RunPlugin(%s)' % (plugin.url_for(add_favourite, favourites_file=output_file, name=label, url=url, thumbnail=thumbnail))))
            items.append(
            {
                'label': unescape(label),
                'path': plugin.url_for('execute',url=unescape(url)),
                'thumbnail':unescape(thumbnail),
                'context_menu': context_items,
            })
    return items

@plugin.route('/add_folder/<path>')
def add_folder(path):
    d = xbmcgui.Dialog()
    folder_name = d.input("New Folder")
    if not folder_name:
        return
    path = "%s%s/" % (path,folder_name)
    xbmcvfs.mkdirs(path)
    folder_icon = get_icon_path('folder')
    xbmcvfs.copy(folder_icon,path+"icon.png")

@plugin.route('/add_library/<path>')
def add_library(path):
    pass

@plugin.route('/add_addons_folder/<favourites_file>/<media>/<path>')
def add_addons_folder(favourites_file,media,path):
    try:
        response = RPC.files.get_directory(media=media, directory=path, properties=["thumbnail"])
    except:
        return
    files = response["files"]
    log(files)
    dir_items = []
    file_items = []
    for f in files:
        label = remove_formatting(f['label'])
        url = f['file']
        thumbnail = f['thumbnail']
        context_items = []
        if f['filetype'] == 'directory':
            if media == "video":
                window = "10025"
            else:
                window = "10502"
            play_url = escape('ActivateWindow(%s,"%s")' % (window,url))
            context_items.append(("[COLOR yellow][B]%s[/B][/COLOR] " % 'Add', 'XBMC.RunPlugin(%s)' % (plugin.url_for(add_favourite, favourites_file=favourites_file, name=label, url=play_url, thumbnail=thumbnail))))
            dir_items.append({
                'label': "[B]%s[/B]" % label,
                'path': plugin.url_for('add_addons_folder', favourites_file=favourites_file, media="files", path=url),
                'thumbnail': f['thumbnail'],
                'context_menu': context_items,
            })
        else:
            play_url = escape('PlayMedia("%s")' % url)
            context_items.append(("[COLOR yellow][B]%s[/B][/COLOR] " % 'Add', 'XBMC.RunPlugin(%s)' % (plugin.url_for(add_favourite, favourites_file=favourites_file, name=label, url=play_url, thumbnail=thumbnail))))
            file_items.append({
                'label': "%s" % label,
                'path': plugin.url_for('play',url=url),
                'thumbnail': f['thumbnail'],
                'context_menu': context_items,
            })
    return dir_items + file_items


@plugin.route('/add_addons/<favourites_file>/<media>')
def add_addons(favourites_file, media):
    type = "xbmc.addon.%s" % media

    response = RPC.addons.get_addons(type=type,properties=["name", "thumbnail"])
    if "addons" not in response:
        return

    addons = response["addons"]

    items = []

    addons = sorted(addons, key=lambda addon: remove_formatting(addon['name']).lower())
    for addon in addons:
        label = addon['name']
        id = addon['addonid']
        thumbnail = addon['thumbnail']
        path = "plugin://%s" % id
        context_items = []
        fancy_label = "[B]%s[/B]" % label
        #context_items.append(("[COLOR yellow][B]%s[/B][/COLOR] " % 'Add', 'XBMC.RunPlugin(%s)' % (plugin.url_for(add_url, id=id, label=label.encode("utf8"), path=path, thumbnail=thumbnail))))
        items.append(
        {
            'label': fancy_label,
            'path': plugin.url_for('add_addons_folder', favourites_file=favourites_file, media="files", path=path),
            'thumbnail': thumbnail,
            'context_menu': context_items,
        })
    return items

@plugin.route('/add/<path>')
def add(path):
    favourites_file = "%sfavourites.xml" % path
    items = []

    for media in ["video", "music"]:
        label = media
        path = "library://%s" % media
        thumbnail = get_icon_path(media)
        items.append(
        {
            'label': "[B]%s Library[/B]" % media.title(),
            'path': plugin.url_for('add_library', path=path),
            'thumbnail': thumbnail,
        })

    for media in ["video", "audio"]:
        label = media
        thumbnail = get_icon_path(media)
        items.append(
        {
            'label': "[B]%s Addons[/B]" % media.title(),
            'path': plugin.url_for('add_addons', favourites_file=favourites_file, media=media),
            'thumbnail': thumbnail,
        })

    items.append(
    {
        'label': "[B]Favourites[/B]",
        'path': plugin.url_for('add_favourites',path=path),
        'thumbnail':get_icon_path('favourites'),
    })

    items.append(
    {
        'label': "New Folder",
        'path': plugin.url_for('add_folder',path=path),
        'thumbnail':get_icon_path('settings'),
    })
    return items

@plugin.route('/')
def index():
    folder_path = "special://profile/addon_data/%s/folders/" % (addon_id())
    return index_of(folder_path)

@plugin.route('/index_of/<path>')
def index_of(path=None):
    items = []

    folders, files = xbmcvfs.listdir(path)
    for folder in sorted(folders):
        folder_path = "%s%s/" % (path,folder)
        thumbnail = "%sicon.png" % folder_path
        items.append(
        {
            'label': folder,
            'path': plugin.url_for('index_of', path=folder_path),
            'thumbnail':thumbnail,
        })
    items = items + favourites(path)

    items.append(
    {
        'label': "Add",
        'path': plugin.url_for('add', path=path),
        'thumbnail':get_icon_path('settings'),
    })

    view = plugin.get_setting('view.type')
    if view != "default":
        plugin.set_content(view)
    return items

if __name__ == '__main__':
    plugin.run()
    if big_list_view == True:
        view_mode = int(plugin.get_setting('view_mode'))
        plugin.set_view_mode(view_mode)