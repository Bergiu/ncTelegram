#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# (unused)
# import os
# import sys
import subprocess
import time
import urwid
import re
import urllib.request
import pytg


# widget used to print the message list
class MessageWidget(urwid.ListBox):
    def __init__(self, Telegram_ui):
        self.urlregex = re.compile("""((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'".,<>?«»“”‘’]))""") # noqa
        self.msgs = []
        self.prev_date = {}
        self.img_buffer = {}
        self.url_buffer = {}
        self.separator_pos = -1
        self.updateLocked = False
        self.Telegram_ui = Telegram_ui
        self.forbidden_msgs = []
        self.forbidden_users = []
        self.load_forbidden_messages()
        self.load_forbidden_users()
        self.get_history()

    def load_forbidden_users(self):
        file_object = open("forbidden_users.txt", "r")
        for user in file_object.read().split("\n"):
            if not user == "":
                print("loaded the forbidden users: " + user)
                self.forbidden_users.append(user)
        file_object.close()

    def load_forbidden_messages(self):
        file_object = open("forbidden_messages.txt", "r")
        for number in file_object.read().split("\n"):
            if not number == "":
                print("loaded the forbidden number: " + number)
                self.forbidden_msgs.append(number)
        file_object.close()

    def appendNumberToForbiddenNumbers(self, number):
        file_object = open("forbidden_messages.txt", "a")
        file_object.write("\n"+number)
        file_object.close()
        print("finished appending number")
        exit()

    def get_history(self):
        while self.updateLocked:
            time.sleep(0.5)
        self.updateLocked = True
        self.separator_pos = -1

        current_cmd = self.Telegram_ui.current_chan['id']
        if current_cmd not in self.prev_date:
            self.prev_date[current_cmd] = 1

        # deletion of previous messages
        self.msg_list = []
        # urwid.SimpleFocusListWalker([urwid.Text(('top', " "), align='left')])
        super().__init__(self.msg_list)

        self.pos = 0

        if current_cmd not in self.Telegram_ui.msg_buffer:
            current_print_name = self.Telegram_ui.current_chan['print_name']
            try:
                msgList = self.Telegram_ui.sender.history(current_print_name, 100) # noqa
            except:
                msgList = []
            self.Telegram_ui.msg_buffer[current_cmd] = msgList

        if current_cmd not in self.Telegram_ui.msg_archive:
            self.Telegram_ui.msg_archive[current_cmd] = []
        else:
            self.print_msg_archive()

        for msg in self.Telegram_ui.msg_buffer[current_cmd]:
            self.print_msg(msg)

        # messages have been printed, deletion form buffer (they are in archive now) # noqa
        self.Telegram_ui.msg_buffer[current_cmd] = []

        self.draw_separator()
        self.updateLocked = False

    def print_msg_archive(self):
        current_cmd = self.Telegram_ui.current_chan['id']
        for msg in self.Telegram_ui.msg_archive[current_cmd]:
            self.msg_list.insert(self.pos + 1, msg)
            self.focus_position = self.pos
            self.pos = self.pos + 1

    def print_msg(self, msg, at_begining=False):

        date = msg['date']

        current_cmd = self.Telegram_ui.current_chan['id']

        if 'text' in msg:
            text = [msg['text']]
            urls = self.urlregex.findall(text[0])

            if urls:
                url = urls[0][0]
                if not url.startswith('http'):
                    url = 'http://' + url

                self.Telegram_ui.last_media[current_cmd] = {'url': url}

                if url in self.url_buffer:
                    if self.url_buffer[url]:
                        text = text + ['\n ➜ ' + self.url_buffer[url]]
                elif date > self.Telegram_ui.boot_time:
                    try:
                        resource = urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Mozilla'})) # noqa
                        page = resource.read().decode(resource.headers.get_content_charset()) # noqa
                        title = re.search('<title>(.*?)</title>', page, re.IGNORECASE|re.DOTALL).group(1) # noqa
                        self.url_buffer[url] = title
                        text = text + ['\n  ➜  ' + title]
                    except:
                        self.url_buffer[url] = ''

        elif 'action' in msg:
            text = [(urwid.AttrSpec('light gray', ''), '➜ ' + msg['action']['type'].replace('_',' '))] # noqa

        elif 'media' in msg:
            self.Telegram_ui.last_media[current_cmd] = msg
            text = [(urwid.AttrSpec('light gray', ''), "➜ " + msg['media']['type'])] # noqa
            if 'caption' in msg['media']:
                text = text + [" " + msg['media']['caption']]

            if self.Telegram_ui.INLINE_IMAGE:
                image = self.get_inline_img(msg)
                if image is not None:
                    text = text + ['\n'] + image

        if 'from' in msg:
            if 'username' in msg['from']:
                from_user = msg['from']['username']
            else:
                from_user = msg['from']['peer_id']
            if 'first_name' in msg['from']:
                sender = msg['from']['first_name']
            else:
                sender = msg['from']['title']
            sender_id = msg['from']['peer_id']
        else:
            if 'username' in msg['sender']:
                from_user = msg['sender']['username']
            else:
                from_user = msg['sender']['peer_id']
            if 'first_name' in msg['sender']:
                sender = msg['sender']['first_name']
            else:
                sender = msg['sender']['title']
            sender_id = msg['sender']['peer_id']
        blocked = False
        if from_user in self.forbidden_users:
            blocked = True
            blocked_msg = "BLOCKED USER"

        color = self.get_name_color(sender_id)

        if 'reply_id' in msg:
            try:
                if msg["reply_id"] in self.forbidden_msgs:
                    text = [(urwid.AttrSpec('light gray', ''), 'reply to ➜  '),
                            (urwid.AttrSpec('light gray', ''), 'deleted msg'),
                            '\n'] + text
                else:
                    msg_reply = self.Telegram_ui.sender.message_get(msg['reply_id']) # noqa

                    if 'from' in msg_reply:
                        if 'first_name' in msg_reply['from']:
                            sender_reply = msg_reply['from']['first_name']
                        else:
                            sender_reply = msg_reply['from']['name']
                        sender_reply_id = msg_reply['from']['peer_id']
                    else:
                        if 'first_name' in msg_reply['sender']:
                            sender_reply = msg_reply['sender']['first_name']
                        else:
                            sender_reply = msg_reply['sender']['name']
                        sender_reply_id = msg_reply['sender']['peer_id']

                    color_reply = self.get_name_color(sender_reply_id)
                    if 'text' in msg_reply:
                        plus = ''
                        if len(msg_reply['text']) > 40:
                            plus = '...'
                        text = [(urwid.AttrSpec('light gray', ''), 'reply to ➜  '), # noqa
                                (urwid.AttrSpec(color_reply, ''), sender_reply), # noqa
                                ': ' + msg_reply['text'][:40] + plus + '\n'] + text # noqa
                    else:
                        text = [(urwid.AttrSpec('light gray', ''), 'reply to ➜  '), # noqa
                                (urwid.AttrSpec(color_reply, ''), sender_reply), # noqa
                                '\n'] + text

            except pytg.exceptions.ConnectionError:
                print("Replyto deleted message, appending number")
                self.appendNumberToForbiddenNumbers(msg["reply_id"])

        if 'fwd_from' in msg:
            color_fwd = self.get_name_color(msg['fwd_from']['peer_id'])
            if 'first_name' in msg['fwd_from']:
                fwd_from_name = msg['fwd_from']['first_name']
            elif 'print_name' in msg['fwd_from']:
                fwd_from_name = msg['fwd_from']['print_name'].replace('_', ' ')
            else:
                fwd_from_name = 'Unknown'

            text = [(urwid.AttrSpec('light gray', ''), 'forwarded from '),
                    (urwid.AttrSpec(color_fwd, ''), fwd_from_name + '\n')] + text # noqa

        cur_date = time.strftime('│ ' + self.Telegram_ui.DATE_FORMAT + ' │', time.localtime(date)) # noqa

        if cur_date != self.prev_date[current_cmd]:
            fill = '─'*(len(cur_date) - 2)
            date_text = '┌' + fill + '┐\n' + cur_date + '\n└' + fill + '┘'

            date_to_display = urwid.Text(('date', date_text), align='center')
            self.msg_list.insert(self.pos + 1, date_to_display)
            self.Telegram_ui.msg_archive[current_cmd].insert(self.pos + 1, date_to_display) # noqa

            self.focus_position = self.pos
            self.pos = self.pos + 1
            self.prev_date[current_cmd] = cur_date

        hour = time.strftime(' %H:%M ', time.localtime(date))

        size_name = 9

        message_meta = urwid.Text([('hour', hour),
                                   (urwid.AttrSpec(color, 'default'), '{0: >9}'.format(sender[0:size_name])), # noqa
                                   ('separator', " │ ")])

        message_text = urwid.Text(text)
        if blocked:
            message_text = urwid.Text(blocked_msg)
        message_to_display = urwid.Columns([(size_name + 10, message_meta), message_text]) # noqa
        if at_begining:
            print_position = 0
        else:
            print_position = self.pos + 1

        self.msg_list.insert(print_position, message_to_display)
        self.Telegram_ui.msg_archive[current_cmd].insert(print_position, message_to_display) # noqa

        self.focus_position = self.pos
        self.pos = self.pos + 1

    def draw_separator(self):
        if self.separator_pos != -1:
            self.delete_separator()
        current_cmd = self.Telegram_ui.current_chan['id']

        if not self.Telegram_ui.NINJA_MODE and current_cmd in self.Telegram_ui.chan_widget.msg_chan: # noqa
            # mark messages as read
            current_print_name = self.Telegram_ui.current_chan['print_name']
            self.Telegram_ui.sender.mark_read(current_print_name)
            self.Telegram_ui.sender.status_online()
            self.Telegram_ui.sender.status_offline()

        self.separator_pos = self.pos

        if current_cmd in self.Telegram_ui.chan_widget.msg_chan:
            self.separator_pos -= self.Telegram_ui.chan_widget.msg_chan[current_cmd] # noqa
            if self.separator_pos <= 0:
                self.separator_pos = 1
            del self.Telegram_ui.chan_widget.msg_chan[current_cmd]
            self.Telegram_ui.chan_widget.update_chan_list()
            self.Telegram_ui.print_title()

        self.pos = self.pos + 1
        self.msg_list.insert(self.separator_pos, urwid.AttrMap(urwid.Divider('-'), 'separator')) # noqa
        self.focus_position = self.separator_pos

    def delete_separator(self):
        if self.separator_pos != -1:
            del self.msg_list[self.separator_pos]
            self.pos = self.pos - 1
            self.separator_pos = -1

    def get_name_color(self, id):
        user_color = self.Telegram_ui.conf['style']['user_color']
        users_color = self.Telegram_ui.conf['style']['users_color']

        if id == self.Telegram_ui.me['peer_id']:
            return user_color

        user_color_list = map(lambda x: x.strip(), user_color.split(','))
        users_color_list = map(lambda x: x.strip(), users_color.split(','))

        user_color = [c for c in user_color_list if 'underline' not in c and 'bold' not in c][0] # noqa
        users_color = [c for c in users_color_list if c not in user_color]

        color = id % len(users_color)
        return users_color[color]

    def get_inline_img(self, msg):
        # cmd = self.Telegram_ui.current_chan['id']
        mid = msg['id']
        key = str(mid)
        if key in self.img_buffer:
            return self.img_buffer[key]
        else:
            path = self.Telegram_ui.download_media(msg)

            if self.Telegram_ui.is_image(path):
                try:
                    raw_text = subprocess.check_output(['img2txt', path, '-f', 'utf8', '-H', '12']) # noqa
                    text = translate_color(raw_text)
                    self.img_buffer[key] = text
                    return text
                except:
                    return None

    def keypress(self, size, key):
        key = super(MessageWidget, self).keypress(size, key)

        if key == self.Telegram_ui.conf['keymap']['down']:
            self.keypress(size, 'down')
        elif key == self.Telegram_ui.conf['keymap']['up']:
            self.keypress(size, 'up')
        elif key == self.Telegram_ui.conf['keymap']['left']:
            self.Telegram_ui.main_columns.focus_position = 0
        else:
            return key

    def mouse_event(self, size, event, button, col, row, focus):

        if button == 4:
            self.keypress(size, 'up')
            self.keypress(size, 'up')

        if button == 5:
            self.keypress(size, 'down')
            self.keypress(size, 'down')


color_list = ['black',
              'dark red',
              'dark green',
              'brown',
              'dark blue',
              'dark magenta',
              'dark cyan',
              'light gray',
              'dark gray',
              'light red',
              'light green',
              'yellow',
              'light blue',
              'light magenta',
              'light cyan',
              'white']


# Translate raw_text (ansi sequence) to something readable by urwid (attribut and text) # noqa
def translate_color(raw_text):
    formated_text = []
    raw_text = raw_text.decode("utf-8")

    for at in raw_text.split("\x1b["):
        try:
            attr, text = at.split("m", 1)
        except:
            attr = '0'
            text = at.split("m", 1)

        list_attr = [int(i) for i in attr.split(';')]
        list_attr.sort()
        fg = -1
        bg = -1

        for elem in list_attr:
            if elem <= 29:
                pass
            elif elem <= 37:
                fg = elem - 30
            elif elem <= 47:
                bg = elem - 40
            elif elem <= 94:
                fg = fg + 8
            elif elem >= 100 and elem <= 104:
                bg = bg + 8
            
        fgcolor = color_list[fg]
        bgcolor = color_list[bg]

        if fg < 0:
            fgcolor = ''
        if bg < 0:
            bgcolor = ''

        if list_attr == [0]:
            fgcolor = ''
            bgcolor = ''

        formated_text.append((urwid.AttrSpec(fgcolor, bgcolor), text))

    return formated_text

# vim: ai ts=4 sw=4 et sts=4
