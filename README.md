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

Install `requests` and `python-dotenv` via `pip`

```bash
pip install requests python-dotenv
```

### Step 2: Configure SSH

Ensure that `ChallengeResponseAuthentication` is set to `yes` in your SSH configuration:

```bash
grep -m 1 ChallengeResponseAuthentication /etc/ssh/sshd_config
```

You should see:

```
ChallengeResponseAuthentication yes
```

### Step 3: Configure PAM for SSHD

Edit `/etc/pam.d/sshd` to include the custom PAM module for Telegram 2FA. Make sure the path to `telegram2fa.py` is correct:

```bash
cat /etc/pam.d/sshd | grep -B 1 -A 1 authentication
```

You should add or find something like:

```
auth requisite /lib/security/pam_python.so /path/to/telegram2fa.py
# Standard Un*x authentication.
@include common-auth
```

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

### Inspiration

This setup was inspired by a post on [hacktracking.blogspot.com](http://hacktracking.blogspot.com/2015/12/ssh-two-factor-authentication-pam.html).
