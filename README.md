# ACM internship Discord bot

This bot checks public GitHub internship lists and posts new roles in `#internship-opportunities`. It does not use AI to write the messages, and it does not log into LinkedIn.

It reads:

- Jobright's public GitHub READMEs for software and data internships
- [SimplifyJobs/Summer2027-Internships](https://github.com/SimplifyJobs/Summer2027-Internships)

The first time it runs, it remembers the jobs already on those lists and sends one line: "Watching for new internships." After that, it checks every hour and posts only new ones, up to 8 each check.

## Setup

1. Install Python 3.11 or newer.
2. Open the [Discord Developer Portal](https://discord.com/developers/applications) → New Application → Bot → Reset Token, and copy the token. Do not share it or commit it.
3. Under Bot → Privileged Gateway Intents, leave Message Content off. This bot only sends messages.
4. OAuth2 → URL Generator. Scopes: `bot`. Bot permissions: Send Messages, Embed Links, View Channels. Open that invite link and add the bot to the ACM server.
5. In Discord, turn on Settings → Advanced → Developer Mode. Right-click `#internship-opportunities` → Copy Channel ID.
6. Copy `.env.example` to `.env` and paste your token and channel id:

```
DISCORD_TOKEN=paste-token-here
CHANNEL_ID=paste-channel-id-here
```

7. From this folder, install once:

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

The bot then starts when you log in to this Mac and checks for new internships every hour. You do not need to run it from a terminal. Output is written to `bot.log`.
