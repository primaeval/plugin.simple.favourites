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

@plugin.route('/play/<url>')
def play(url):
    xbmc.executebuiltin('PlayMedia("%s")' % url)

@plugin.route('/execute/<url>')
def execute(url):
    xbmc.executebuiltin(url)

@plugin.route('/favourites/<folder_path>')
def favourites(folder_path):
    items = []
    if plugin.get_setting('kodi.favourites') == 'true':
        f = xbmcvfs.File("%sfavourites.xml" % folder_path,"rb")
        data = f.read()
        favourites = re.findall("<favourite.*?</favourite>",data)
        for fav in favourites:
            fav = re.sub('&quot;','"',fav)
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
                items.append(
                {
                    'label': label,
                    'path': plugin.url_for('execute',url=url),
                    'thumbnail':thumbnail,
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