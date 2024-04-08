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


def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        'chat_id': CHAT_ID,
        'text': message,
        'parse_mode': 'Markdown'
    }
    response = requests.post(url, data=payload)
    return response.ok


def can_attempt_interactive():
    while not BUCKET.consume():
        print_with_message("You are trying too fast. Please wait.")
        time.sleep(1)


def get_otp():
    return str(random.randint(100000, 999999))


def print_with_message(message):
    send_telegram_message(f"{message} from {CONNECTION_INFO}")
    print(message)


def check_auth(pamh):
    otp = get_otp()
    if send_telegram_message(f"Your OTP is: {otp}"):
        print("OTP sent to your Telegram chat.")
    else:
        print("Failed to send OTP.")

    for _ in range(INCORRECT_ATTEMPTS):
        can_attempt_interactive()
        msg = pamh.Message(pamh.PAM_PROMPT_ECHO_OFF, 'Enter OTP: ')
        rsp = pamh.conversation(msg)
        if msg == rsp.resp:
            print_with_message("Login Successful!")
            return True
        else:
            print_with_message("Incorrect OTP. Try again.")
    else:
        can_attempt_interactive()
        print_with_message(f"{INCORRECT_ATTEMPTS} incorrect OTP attempts. Try the urgent key.")
        urgent_input = input("Enter Urgent Key: ")
        if urgent_input == URGENT_KEY:
            print_with_message("Urgent login successful.")
            return True
        else:
            print_with_message("Incorrect Urgent Key. Access Denied.")
            return False
    # unreachable code, for situation when code above changes
    print_with_message("Access Denied.")
    return False


def log(message):
    path = "/tmp/pam_debug"
    current_time = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(path, "ab") as file:
        file.write(f"{current_time} {message}\n".encode("utf-8"))


def pam_sm_authenticate(pamh, flags, argv):
    local_network = '192.168.1.'
    if local_network in pamh.rhost:
        return pamh.PAM_SUCCESS

    if check_auth(pamh):
        return pamh.PAM_SUCCESS
    return pamh.PAM_AUTH_ERR


def pam_sm_setcred(pamh, flags, argv):
    return pamh.PAM_SUCCESS


def pam_sm_acct_mgmt(pamh, flags, argv):
    return pamh.PAM_SUCCESS


def pam_sm_open_session(pamh, flags, argv):
    return pamh.PAM_SUCCESS


def pam_sm_close_session(pamh, flags, argv):
    return pamh.PAM_SUCCESS


def pam_sm_chauthtok(pamh, flags, argv):
    return pamh.PAM_SUCCESS

log("telegram2fa.py loaded")
load_dotenv()
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
URGENT_KEY = os.getenv('URGENT_KEY')
INCORRECT_ATTEMPTS = int(os.getenv('INCORRECT_ATTEMPTS'))
BUCKET = TokenBucket(3, 1)  # 3 tokens, refilling at 1 token per second

CONNECTION_INFO = os.environ.get('SSH_CONNECTION')
CONNECTION_INFO += (f", host: {os.environ.get('PAM_RHOST')}, user: {os.environ.get('PAM_RUSER')}"
                    f", service: {os.environ.get('PAM_SERVICE')}, tty: {os.environ.get('PAM_TTY')}"
                    f", user: {os.environ.get('PAM_USER')}, type: {os.environ.get('PAM_TYPE')}")

log(f"{CONNECTION_INFO=}")
log(f"{TELEGRAM_TOKEN=}")
log(f"{CHAT_ID=}")
log(f"{URGENT_KEY=}")
log(f"{INCORRECT_ATTEMPTS=}")
log(f"{os.getcwd()=}")


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
# # systemctl restart sshd
# inspiration: http://hacktracking.blogspot.com/2015/12/ssh-two-factor-authentication-pam.html
