#!/bin/python3
import os
import random
import time
import requests

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    print("Please install the required modules using the following command:")
    print("pip install python-dotenv")
    exit(1)


class TokenBucket:
    def __init__(self, capacity, fill_rate):
        self.capacity = capacity
        self._tokens = capacity
        self.fill_rate = fill_rate
        self.last_update = time.time()

    def consume(self, tokens=1):
        self._update_tokens()
        if tokens <= self._tokens:
            self._tokens -= tokens
            return True
        return False

    def _update_tokens(self):
        now = time.time()
        elapsed = now - self.last_update
        self._tokens = min(self.capacity, self._tokens + elapsed * self.fill_rate)
        self.last_update = now


def can_attempt():
    return BUCKET.consume()


def send_telegram_message(message, reply_markup=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        'chat_id': CHAT_ID,
        'text': message,
        'reply_markup': reply_markup
    }
    response = requests.post(url, json=payload)
    if not response.ok:
        print_with_message(f"Error message: {response.text}", None)
    return response.ok


def can_attempt_interactive(pamh):
    while not BUCKET.consume():
        print_with_message("You are trying too fast. Please wait.", pamh)
        time.sleep(1)


def print_with_message(message, pamh):
    if pamh is not None:
        user, ip, service, tty = get_connection_info(pamh)
    else:
        user, ip, service, tty = None, None, None, None
    connection_info = f"User: {user}\nIP: {ip}\nService: {service}\nTTY: {tty}"
    send_telegram_message(f"{message}\n{connection_info}")
    print(message)
    log(message)


def get_messages(pamh):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    response = requests.get(url)
    try:
        return response.json()
    except ValueError:
        print_with_message(f"Error: {response.text}", pamh)
        return None


def set_all_as_read(last_update_id):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    payload = {
        'offset': last_update_id
    }
    response = requests.post(url, data=payload)
    return response.ok


def get_last_update_id(messages):
    if messages is None:
        return None
    try:
        return messages['result'][-1]['update_id']
    except IndexError:
        return None


def filter_messages(messages):
    if messages is None:
        return None
    filtered_messages = []
    for message in messages['result']:
        try:
            chat_id = message['message']['chat']['id']
        except KeyError:
            chat_id = message['callback_query']['message']['chat']['id']
        if str(chat_id) == CHAT_ID:
            filtered_messages.append(message)
    return filtered_messages


def create_reply_markup(list_of_rows):
    reply_markup = {}
    inline_keyboard = []
    for row in list_of_rows:
        current_row = []
        for button in row:
            current_row.append({'text': button, 'callback_data': button})
        inline_keyboard.append(current_row)
    reply_markup['inline_keyboard'] = inline_keyboard
    return reply_markup


def get_connection_info(pamh):
    
    try:
        user = pamh.get_user(None)
    except pamh.exception:
        user = None

    try:
        ip = pamh.rhost
    except pamh.exception:
        ip = None

    try:
        service = pamh.service
    except pamh.exception:
        service = None

    try:
        tty = pamh.tty
    except pamh.exception:
        tty = None

    return user, ip, service, tty


def check_auth(pamh):
    if FORCE_AUTH_PAM:
        log("FORCE_AUTH {}".format(FORCE_AUTH_PAM))
        return True
    try:
        can_attempt_interactive(pamh)

        user, ip, service, tty = get_connection_info(pamh)

        messages = get_messages(pamh)
        log(f"{messages=}")
        last_update_id = get_last_update_id(messages)
        log(f"{last_update_id=}")
        set_all_as_read(last_update_id)
        log("set_all_as_read")

        keyboard_buttons = [['Yes', 'No']]
        log(f"{keyboard_buttons=}")
        reply_markup = create_reply_markup([keyboard_buttons])
        log(f"{reply_markup=}")
        send_telegram_message(f"User: {user}\nIP: {ip}\nService: {service}\nTTY: {tty}", reply_markup)
        log("send_telegram_message")

        while True:
            log("while True")
            messages = get_messages(pamh)
            log(f"{messages=}")
            last_update_id = get_last_update_id(messages)
            log(f"{last_update_id=}")
            set_all_as_read(last_update_id)
            log("set_all_as_read")
            filtered_messages = filter_messages(messages)
            log(f"{filtered_messages=}")
            if filtered_messages:
                log("filtered_messages")
                for message in filtered_messages:
                    log(f"{message=}")
                    try:
                        reply = message['callback_query']['data']
                    except KeyError:
                        reply = None
                    if reply == 'Yes':
                        log("Yes")
                        return True
                    elif reply == 'No':
                        log("No")
                        return False
            else:
                log("else")
            send_telegram_message("Please reply with 'Yes' or 'No'.", reply_markup)
            log("send_telegram_message")
            time.sleep(1)

        # unreachable code, for situation when code above changes
        log("unreachable code")
        print_with_message("Access Denied.", pamh)
        return False
    except BaseException as e:
        message = f"Error: {e}"
        print_with_message(message, pamh)
        return False


def log(message):
    path = "/tmp/pam_debug"
    current_time = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(path, "ab") as file:
        file.write(f"{current_time} {message}\n".encode("utf-8"))


def pam_sm_authenticate(pamh, flags, argv):
    print_with_message(f"pam_sm_authenticate", pamh)
    local_network = '192.168.1.'
    _ = flags
    _ = argv
    if local_network in pamh.rhost:
        return pamh.PAM_SUCCESS
    
    result = check_auth(pamh)
    
    print_with_message(f"{result=}", pamh)

    if result:
        print_with_message("return pamh.PAM_SUCCESS", pamh)
        return pamh.PAM_SUCCESS
    print_with_message("return pamh.PAM_AUTH_ERR", pamh)
    return pamh.PAM_AUTH_ERR


def pam_sm_setcred(pamh, flags, argv):
    _ = flags
    _ = argv
    return pamh.PAM_SUCCESS


def pam_sm_acct_mgmt(pamh, flags, argv):
    _ = flags
    _ = argv
    return pamh.PAM_SUCCESS


def pam_sm_open_session(pamh, flags, argv):
    _ = flags
    _ = argv
    return pamh.PAM_SUCCESS


def pam_sm_close_session(pamh, flags, argv):
    _ = flags
    _ = argv
    return pamh.PAM_SUCCESS


def pam_sm_chauthtok(pamh, flags, argv):
    _ = flags
    _ = argv
    return pamh.PAM_SUCCESS


load_dotenv()
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
URGENT_KEY = os.getenv('URGENT_KEY')
FORCE_AUTH_PAM = os.getenv('FORCE_AUTH_PAM')
FORCE_AUTH_PAM = FORCE_AUTH_PAM.lower() == 'true'
try:
    INCORRECT_ATTEMPTS = int(os.getenv('INCORRECT_ATTEMPTS'))
except TypeError:
    INCORRECT_ATTEMPTS = 1
BUCKET = TokenBucket(3, 1)  # 3 tokens, refilling at 1 token per second


# if "PAM_DEBUG" in os.environ:
#     print_with_message(f"{CONNECTION_INFO=}")
#     print_with_message(f"{TELEGRAM_TOKEN=}")
#     print_with_message(f"{CHAT_ID=}")
#     print_with_message(f"{URGENT_KEY=}")
#     print_with_message(f"{INCORRECT_ATTEMPTS=}")
#     print_with_message(f"{os.getcwd()=}")

# usage:
# # apt-get install libpam-python
#
# # grep -m 1 ChallengeResponseAuthentication /etc/ssh/sshd_config
# ChallengeResponseAuthentication yes
#
# # cat /etc/pam.d/sshd | grep -B 1 -A 1 authentication
# auth requisite /lib/security/pam_python.so /path/to/telegram2fa.py
# # Standard Un*x authentication.
# @include common-auth
#
# cat /.env
# TELEGRAM_TOKEN="your_token_here"
# CHAT_ID=your_chat_id_here
# URGENT_KEY="your_urgent_key_here"
# INCORRECT_ATTEMPTS=3
#
# # systemctl restart sshd
# inspiration: http://hacktracking.blogspot.com/2015/12/ssh-two-factor-authentication-pam.html
