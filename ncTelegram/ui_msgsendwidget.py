#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import os.path
import time
import re
import urwid

TEXT_CAPTION = " >> "


class MessageSendWidget(urwid.Filler):
    def __init__(self, Telegram_ui):
        self.Telegram_ui = Telegram_ui
        self.updateLockedauto = False
        self.username_list = []
        self.buffer_writing_text = {}

        # handeling navigation in history
        self.history_own_message = {}
        self.history_pos = 0
        self.cur_text = ""

        self.status_bar = urwid.Text(('status_bar', ' '), align='left')
        self.attr = urwid.AttrMap(self.status_bar, 'status_bar')

        self.widgetEdit = urwid.Edit(TEXT_CAPTION, "", multiline=False)

        self.pile = urwid.Pile([self.attr, self.widgetEdit])
        super().__init__(self.pile)

        self.update_send_widget()

    def update_send_widget(self):
        if 'when' in self.Telegram_ui.current_chan:
            self.current_status = (self.Telegram_ui.current_chan['when'], False) # noqa
        else:
            self.current_status = ('?', False)

        self.widgetEdit.set_edit_text('')
        self.username_list = []

        cmd = self.Telegram_ui.current_chan['id']
        if cmd in self.buffer_writing_text:
            self.widgetEdit.insert_text(self.buffer_writing_text[cmd])

        if cmd not in self.history_own_message:
            self.history_own_message[cmd] = []
            for msg in self.Telegram_ui.msg_buffer[cmd]:
                if 'text' in msg and 'from' in msg and msg['from']['id'] == self.Telegram_ui.me['id']: # noqa
                    self.history_own_message[cmd].append(msg['text'])

        self.history_pos = 0
        self.update_status_bar()

    def update_status_bar(self):
        chan_name = self.Telegram_ui.current_chan['print_name'].replace('_', ' ') # noqa
        chan_type = self.Telegram_ui.current_chan['peer_type']
        current_cmd = self.Telegram_ui.current_chan['id']

        if chan_type == 'chat':
            chan_num = self.Telegram_ui.current_chan['members_num']
            text = ' [ ' + chan_name + " ] --- [ " + str(chan_num) + " members ]" # noqa
        elif chan_type == 'user':
            text = ' [ ' + chan_name + ' ]'
            (when, status) = self.Telegram_ui.online_status[current_cmd]

            if status:
                text = text + ' --- [ Online ]'
            elif when == '?':
                text = text + ' --- [ Offline ]'
            else:
                current_date = time.strftime(self.Telegram_ui.DATE_FORMAT, time.localtime(int(time.time()))) # noqa
                pattern = '%Y-%m-%d %H:%M:%S'
                when_epoch = int(time.mktime(time.strptime(when, pattern)))
                when_date = time.strftime(self.Telegram_ui.DATE_FORMAT, time.localtime(when_epoch)) # noqa
                when_hour = time.strftime('%H:%M', time.localtime(when_epoch))

                if when_date == current_date:
                    text = text + ' --- [ last seen at ' + when_hour + ' ]'
                else:
                    text = text + ' --- [ last seen ' + when_date + ' at ' + when_hour + ' ]' # noqa
        elif chan_type == 'channel':
            chan_num = self.Telegram_ui.current_chan['participants_count']
            # fix bug in dialog_list in telegram_cli 
            if chan_num == 0:
                chan_num = self.Telegram_ui.sender.channel_info(chan_name.replace(' ', '_'))['participants_count'] # noqa
                self.Telegram_ui.current_chan['participants_count'] = chan_num 
            text = ' [ ' + chan_name + " ] --- [ " + str(chan_num) + " participants ]" # noqa

        if current_cmd in self.Telegram_ui.read_status and self.Telegram_ui.read_status[current_cmd]: # noqa
            text = text + '  ✓'

        self.status_bar.set_text(text)
        try:
            self.Telegram_ui.main_loop.draw_screen()
        except:
            pass

    def history_prev(self):
        cmd = self.Telegram_ui.current_chan['id']

        if -self.history_pos == len(self.history_own_message[cmd]):
            return

        if self.history_pos == 0:
            self.cur_text = self.widgetEdit.get_edit_text()

        self.history_pos -= 1
        new_text = self.history_own_message[cmd][self.history_pos]
        self.widgetEdit.set_edit_text('')
        self.widgetEdit.insert_text(new_text)

    def history_next(self):
        cmd = self.Telegram_ui.current_chan['id']
 
        if self.history_pos == 0:
            return

        self.history_pos += 1
        if self.history_pos == 0:
            new_text = self.cur_text
        else:
            new_text = self.history_own_message[cmd][self.history_pos]

        self.widgetEdit.set_edit_text('')
        self.widgetEdit.insert_text(new_text)

    def autocomplete(self):
        if self.updateLockedauto:
            return

        self.updateLockedauto = True

        # check if the list of username is already there
        if self.username_list == []:
            type_chan = self.Telegram_ui.current_chan['peer_type']
            print_name_chan = self.Telegram_ui.current_chan['print_name']

            # get possible username
            if type_chan == 'chat':
                chat_info = self.Telegram_ui.sender.chat_info(print_name_chan)
                for user in chat_info['members']:
                    if 'username' in user and user['username'] is not None:
                        self.username_list.append(user['username'])

            elif type_chan == 'user' and 'username' in self.Telegram_ui.current_chan: # noqa
                self.username_list = [self.Telegram_ui.current_chan['username']] # noqa

            elif type_chan == 'channel':
                try:
                    members = self.Telegram_ui.sender.channel_get_members(print_name_chan) # noqa
                except:
                    members = []
                for user in members:
                    if 'username' in user and user['username'] is not None:
                        self.username_list.append(user['username'])

        text = self.widgetEdit.get_edit_text()[1:]
        text = self.widgetEdit.get_edit_text().rsplit(' ', 1)[-1][1:]
        self.updateLockedauto = False

        # autocompletion with the first match
        for user in self.username_list:
            if user.startswith(text):
                to_complete = user[len(text):]
                self.widgetEdit.insert_text(to_complete + ' ')
                break

    def resize_zone(self, size):

        rows_needed = int((len(self.widgetEdit.get_edit_text()) + len(TEXT_CAPTION)) / size[0]) +2 # noqa
        if rows_needed > 10:
            rows_needed = 10
        if rows_needed != size[1]:
            self.Telegram_ui.right_side.contents[1] = (self.Telegram_ui.right_side.contents[1][0], ('given', rows_needed)) # noqa

    def keypress(self, size, key):
        key = super(MessageSendWidget, self).keypress(size, key)

        dst = self.Telegram_ui.current_chan['print_name']

        if not self.Telegram_ui.NINJA_MODE:
            # try/expect needed when user lacks of priviledge on channels
            try:
                if len(self.widgetEdit.get_edit_text()) == 1:
                    self.Telegram_ui.sender.send_typing(dst)
                elif len(self.widgetEdit.get_edit_text()) == 0:
                    self.Telegram_ui.sender.send_typing_abort(dst)
            except:
                pass

        if key == 'enter':
            msg = self.widgetEdit.get_edit_text()

            if not self.Telegram_ui.NINJA_MODE:
                self.Telegram_ui.sender.status_online()
                self.Telegram_ui.sender.status_offline()
                self.Telegram_ui.sender.mark_read(dst)

            # Send file
            msg = re.sub(r'\s+$', '', msg)
            if msg.startswith("'") and msg.endswith("'") and\
                    os.path.isfile(msg[1:][:-1]):

                self.widgetEdit.insert_text(" Please wait...")
                self.Telegram_ui.main_loop.draw_screen()
                # try/expect needed when user lacks of priviledge on channels
                try: 
                    self.Telegram_ui.sender.send_file(dst, msg[1:][:-1])
                except:
                    pass
            else:
                # try/expect needed when user lacks of priviledge on channels
                try:
                    self.Telegram_ui.sender.send_msg(dst, msg, enable_preview=True) # noqa
                except:
                    pass

            current_cmd = self.Telegram_ui.current_chan['id']
            if current_cmd in self.history_own_message:
                self.history_own_message[current_cmd].append(msg)
            else:
                self.history_own_message[current_cmd] = [msg]

            self.widgetEdit.set_edit_text("")
            self.cur_text = ""

        # linebreaks
        elif key == self.Telegram_ui.conf['keymap']['line_break']:
            self.widgetEdit.insert_text("\n")

        # Autocompletion
        elif key == 'tab' and self.widgetEdit.get_edit_text().rsplit(' ', 1)[-1].startswith("@"): # noqa
            self.autocomplete()

        # deletion of current text
        elif key == 'ctrl u':
            self.widgetEdit.set_edit_text("")

        # deletion of characters left of the cursor until the next stop character # noqa
        elif key == 'ctrl w':
            STOPCHARACTERS = r'[\s\W]'

            edit_text = self.widgetEdit.get_edit_text()

            # the widget considers the caption when calculating the cursor position # noqa
            cursor_pos = self.widgetEdit.get_cursor_coords((size[0],))[0] - len(TEXT_CAPTION) # noqa
            i = 0
            for character in reversed(edit_text[:cursor_pos]):
                if i > 0 and re.match(STOPCHARACTERS, character):
                    break
                else:
                    i += 1

            new_edit_text = edit_text[:cursor_pos - i] + edit_text[cursor_pos:]
            self.widgetEdit.set_edit_text(new_edit_text)
            self.widgetEdit.set_edit_pos(cursor_pos - i)

        # gives the focus to the message list
        elif key == 'up' or key == 'page up' or key == 'esc':
            self.Telegram_ui.right_side.focus_position = 0

        elif key == 'left':
            self.Telegram_ui.main_columns.focus_position = 0

        # navigation in your own history
        elif key == 'shift up':
            self.history_prev()

        elif key == 'shift down':
            self.history_next()

        else:
            self.resize_zone(size)
            return key

# vim: ai ts=4 sw=4 et sts=4
