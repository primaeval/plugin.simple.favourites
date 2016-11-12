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

def log(v):
    xbmc.log(repr(v))


def get_icon_path(icon_name):
    addon_name = xbmcaddon.Addon().getAddonInfo('id')
    if plugin.get_setting('user.icons') == "true":
        user_icon = "special://profile/addon_data/%s/icons/%s.png" % (addon_name,icon_name)
        if xbmcvfs.exists(user_icon):
            return user_icon
    return "special://home/addons/%s/resources/img/%s.png" % (addon_name,icon_name)


def remove_formatting(label):
    label = re.sub(r"\[/?[BI]\]",'',label)
    label = re.sub(r"\[/?COLOR.*?\]",'',label)
    return label

def escape( str ):
    str = str.replace("<", "&lt;")
    str = str.replace(">", "&gt;")
    str = str.replace("&", "&amp;")
    str = str.replace("\"", "&quot;")
    return str

@plugin.route('/play/<url>')
def play(url):
    xbmc.executebuiltin('PlayMedia("%s")' % url)

@plugin.route('/execute/<url>')
def execute(url):
    xbmc.executebuiltin(url)

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
    new_name = d.input("New Name for: %s" % name,name)
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

@plugin.route('/change_favourite_icon/<favourites_file>/<name>/<url>')
def change_favourite_icon(favourites_file,name,url):
    f = xbmcvfs.File(favourites_file,"rb")
    data = f.read()
    f.close()
    data = re.sub('.*<favourite name="%s".*?>%s</favourite>.*\n' % (re.escape(name),re.escape(url)),'',data)
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
                thumbnail = ''
                url = match.group(2)
        if url:
            context_items = []
            context_items.append(("[COLOR yellow][B]%s[/B][/COLOR] " % 'Remove', 'XBMC.RunPlugin(%s)' % (plugin.url_for(remove_favourite, favourites_file=favourites_file, name=label, url=url))))
            context_items.append(("[COLOR yellow][B]%s[/B][/COLOR] " % 'Rename', 'XBMC.RunPlugin(%s)' % (plugin.url_for(rename_favourite, favourites_file=favourites_file, name=label, fav=fav))))
            context_items.append(("[COLOR yellow][B]%s[/B][/COLOR] " % 'Change Icon', 'XBMC.RunPlugin(%s)' % (plugin.url_for(change_favourite_icon, favourites_file=favourites_file, name=label, url=url))))
            label = re.sub('&quot;','"',label)
            url = re.sub('&quot;','"',url)
            thumbnail = re.sub('&quot;','"',thumbnail)
            items.append(
            {
                'label': label,
                'path': plugin.url_for('execute',url=url),
                'thumbnail':thumbnail,
                'context_menu': context_items,
            })
    return items


@plugin.route('/add_item/<title>/<path>/icon')
def add_item(title,path,icon):
    pass

@plugin.route('/add_folder')
def add_folder():
    d = xbmcgui.Dialog()
    folder_name = d.input("New Folder")
    if not folder_name:
        return
    addon_name = xbmcaddon.Addon().getAddonInfo('id')
    path = "special://profile/addon_data/%s/folders/%s/" % (addon_name,folder_name)
    xbmcvfs.mkdirs(path)
    folder_icon = get_icon_path('folder')
    xbmcvfs.copy(folder_icon,path+"icon.png")

@plugin.route('/add')
def add():
    items = []

    items.append(
    {
        'label': "Add Folder",
        'path': plugin.url_for('add_folder'),
        'thumbnail':get_icon_path('settings'),
    })
    return items


@plugin.route('/')
def index():
    return index_of()

@plugin.route('/index_of/<path>')
def index_of(path=None):
    input_path = path
    items = []

    if input_path:
        folder_path = input_path
    else:
        addon_name = xbmcaddon.Addon().getAddonInfo('id')
        folder_path = "special://profile/addon_data/%s/folders/" % (addon_name)

    folders, files = xbmcvfs.listdir(folder_path)
    for folder in sorted(folders):
        path = "%s/%s/" % (folder_path,folder)
        thumbnail = "%sicon.png" % path
        items.append(
        {
            'label': folder,
            'path': plugin.url_for('index_of', path=path),
            'thumbnail':thumbnail,
        })

    if input_path:
        favourites_path = input_path
    else:
        favourites_path = "special://profile/"

    items = items + favourites(favourites_path)

    items.append(
    {
        'label': "Add",
        'path': plugin.url_for('add'),
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