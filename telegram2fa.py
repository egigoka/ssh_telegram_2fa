#!/bin/python3
import os
import time
import requests
import socket
import netifaces

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


def request_with_retry(func, url, json=None, params=None):
    while True:
        response = func(url, json=json, params=params)

        if not response.ok:
            time.sleep(1)
            log(f"Error message: {response.text}")
            continue

        try:
            response.json()
            return response
        except ValueError:
            time.sleep(1)
            log(f"Error message: {response.text}")
            continue


def send_telegram_message(message, reply_markup=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        'chat_id': CHAT_ID,
        'text': message
    }
    if reply_markup is not None:
        payload['reply_markup'] = reply_markup

    response = request_with_retry(requests.post, url, json=payload)

    return response


def update_telegram_message(message_id, new_message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/editMessageText"
    payload = {
        "chat_id": CHAT_ID,
        "message_id": message_id,
        "text": new_message
    }

    response = request_with_retry(requests.post, url, json=payload)

    return response


def can_attempt_interactive(pamh):
    while not BUCKET.consume():
        print_with_message("cannot get token for attempt, waiting", pamh=pamh)
        time.sleep(1)


def format_message(message, pamh):
    if pamh is not None:
        user, ip, service, tty = get_connection_info(pamh=pamh)
    else:
        user, ip, service, tty = None, None, None, None

    server_hostname, server_ips = get_network_info()

    connection_info = f"User: {user}\nIP: {ip}\nService: {service}\nTTY: {tty}"
    server_info = f"Hostname: {server_hostname}\nIPs: {', '.join(server_ips)}"

    message = "" if not message else message + "\n\n"

    return f"{message}{connection_info}\n{server_info}"


def print_with_message(message, pamh):
    formatted_message = format_message(message, pamh=pamh)
    send_telegram_message(formatted_message)
    print(formatted_message)
    log(formatted_message)


def get_messages(last_update_id=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    payload = {
        'offset': last_update_id
    }
    response = request_with_retry(requests.get, url, params=payload)
    return response.json()


def get_last_update_id(messages, fallback=None):
    if messages is None:
        return fallback
    try:
        return messages['result'][-1]['update_id']
    except IndexError:
        return fallback


def filter_messages(messages, message_id_to_callback):
    if messages is None:
        return None
    filtered_messages = []
    for message in messages['result']:
        try:
            chat_id = message['message']['chat']['id']
        except KeyError:
            chat_id = message['callback_query']['message']['chat']['id']
        try:
            message_id = message["message"]["message_id"]
        except KeyError:
            message_id = message["callback_query"]["message"]["message_id"]
        if str(chat_id) == CHAT_ID and message_id == message_id_to_callback:
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
    if pamh is None:
        return None, None, None, None

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


def get_network_info():
    host_name = socket.gethostname()
    ip_addresses = []

    # Iterate over all interfaces and get the IP addresses (skip loopback).
    for interface in netifaces.interfaces():
        addresses = netifaces.ifaddresses(interface)
        ipv4_info = addresses.get(netifaces.AF_INET)
        if ipv4_info:
            for address in ipv4_info:
                ip_addr = address['addr']
                if ip_addr != "127.0.0.1":
                    ip_addresses.append(ip_addr)

    return host_name, ip_addresses


def get_filtered_messages(last_update_id, message_id_to_callback):
    messages = get_messages(last_update_id + 1 if last_update_id is not None else last_update_id)
    last_update_id = get_last_update_id(messages, fallback=last_update_id)
    filtered_messages = filter_messages(messages, message_id_to_callback)
    return last_update_id, filtered_messages


def check_auth(pamh):
    message_id = None
    if FORCE_AUTH_PAM:
        return True, message_id
    try:
        can_attempt_interactive(pamh=pamh)

        messages = get_messages()
        last_update_id = get_last_update_id(messages)

        keyboard_buttons = [['Yes', 'No']]
        reply_markup = create_reply_markup(keyboard_buttons)
        formatted_message = format_message(None, pamh=pamh)

        sent_message = send_telegram_message(f"{formatted_message}"
                                             f"\n\nAuthorize?",
                                             reply_markup)
        message_id = sent_message.json()["result"]["message_id"]

        while True:
            last_update_id, filtered_messages = get_filtered_messages(last_update_id, message_id)

            if filtered_messages:
                for message in filtered_messages[::-1]:
                    try:
                        reply = message['callback_query']['data']
                    except KeyError:
                        reply = None
                    if reply == 'Yes':
                        return True, message_id
                    elif reply == 'No':
                        return False, message_id
            time.sleep(1)

        # unreachable code, for situation when code above changes
        print_with_message("Access Denied.", pamh=pamh)
        return False, message_id
    except BaseException as e:
        message = f"Error: {e}"
        print_with_message(message, pamh=pamh)
        return False, message_id


def log(message):
    path = "/tmp/pam_debug"
    current_time = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(path, "ab") as file:
        message = f"{current_time} {message}\n"
        print(message, end="", flush=True)
        file.write(message.encode("utf-8"))


def pam_sm_authenticate(pamh, flags, argv):
    local_network = '192.168.1.'
    _ = flags
    _ = argv
    if local_network in pamh.rhost:
        return pamh.PAM_SUCCESS

    result, message_id = check_auth(pamh=pamh)

    if result:
        formatted_message = format_message("Access Granted.", pamh=pamh)
        print(formatted_message)
        log(formatted_message)
        update_telegram_message(message_id, formatted_message)
        return pamh.PAM_SUCCESS

    formatted_message = format_message("Access Denied.", pamh=pamh)
    print(formatted_message)
    log(formatted_message)
    update_telegram_message(message_id, formatted_message)
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
try:
    FORCE_AUTH_PAM = os.getenv('FORCE_AUTH_PAM').lower() == 'true'
except AttributeError:
    FORCE_AUTH_PAM = False
try:
    INCORRECT_ATTEMPTS = int(os.getenv('INCORRECT_ATTEMPTS'))
except TypeError:
    INCORRECT_ATTEMPTS = 1
BUCKET = TokenBucket(3, 1)  # 3 tokens, refilling at 1 token per second
