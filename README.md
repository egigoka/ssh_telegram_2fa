## Motivation

Naive implementation of PAM module on Python. Done in fashion that doesn't use interactive functionality of PAM such as `conversation` and `Message` as a workaround for [this bug](https://sourceforge.net/p/pam-python/tickets/6/).

## TODO
 [ ] Add tests
 
 [ ] Make subnets for which 2fa is skipped configurable

 [ ] As I see now, without interactiveness, you can't bypass this in case internet connection or access to Telegram account is down

 [ ] Different users may want to use different Telegram accounts to review access requests

 [ ] Make proper logging instead of dumping it into /tmp (I'm sorry, I'm not a very skilled Linux developer heh)

 [ ] Maybe, storing config in root (it was default working directory for PAM) isn't my brightest idea

## Usage

### Step 1: Install dependencies

Install `libpam-python` to enable PAM (Pluggable Authentication Module) support for Python scripts:

```bash
apt-get install libpam-python
```

There is only community package of python3 variant of pam_python for openSUSE, so use at your own risk.
```bash
zypper addrepo https://download.opensuse.org/repositories/home:badshah400:howdy/openSUSE_Tumbleweed/home:badshah400:howdy.repo
zypper refresh
zypper install pam-python3
```

Install `requests`, `python-dotenv` and `netifaces` via `pip` as root.

```bash
pip install requests python-dotenv netifaces
```

### Step 2: Configure SSH

Ensure that `ChallengeResponseAuthentication` is set to `yes` in your SSH configuration:

```bash
grep -m 1 ChallengeResponseAuthentication /etc/ssh/sshd_config
```

on some distributions file can be in `/usr/etc/ssh/sshd_config`

You should see or add this:

```
ChallengeResponseAuthentication yes
```

### Step 3: Configure PAM for SSHD

Edit `/etc/pam.d/sshd` to include the custom PAM module for Telegram 2FA. Make sure the path to `telegram2fa.py` is correct:

On some distributions it can be in `/usr/lib/pam.d/sshd`

```bash
cat /etc/pam.d/sshd | grep -B 1 -A 1 authentication
```

You should add or find something like:

```
auth requisite /lib/security/pam_python.so /path/to/telegram2fa.py
# Standard Un*x authentication.
@include common-auth
```

On openSUSE community package lib is in `/usr/lib64/security/pam_python3.so`

### Step 4: Set Environment Variables

Create a `.env` file with your Telegram bot token, chat ID, and other configuration settings:

```plaintext
# /.env file content
TELEGRAM_TOKEN="your_token_here"
CHAT_ID=your_chat_id_here
INCORRECT_ATTEMPTS=3
FORCE_AUTH_PAM=False
```

### Step 5: Restart SSH Service

Apply the changes by restarting the SSH daemon:

```bash
systemctl restart sshd
```

### Debug
To read auth logs, run `journalctl SYSLOG_FACILITY=10`
To read scripts logs, run `cat /tmp/pam_debug`

### Inspiration

This setup was inspired by a post on [hacktracking.blogspot.com](http://hacktracking.blogspot.com/2015/12/ssh-two-factor-authentication-pam.html).
