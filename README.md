---

## Usage

### Step 1: Install PAM Python

Install `libpam-python` to enable PAM (Pluggable Authentication Module) support for Python scripts:

```bash
apt-get install libpam-python
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

Create a `.env` file with your Telegram bot token, chat ID, urgent key, and other configuration settings:

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

This setup was inspired by an article on [hacktracking.blogspot.com](http://hacktracking.blogspot.com/2015/12/ssh-two-factor-authentication-pam.html) about SSH two-factor authentication using PAM.

---
