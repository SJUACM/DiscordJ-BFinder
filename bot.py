import json
import os

import discord
from discord.ext import tasks
from dotenv import load_dotenv

import jobs

FOLDER = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(FOLDER, ".env"))

TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
SEEN_FILE = os.path.join(FOLDER, "seen.json")
MAX_POSTS = 8

intents = discord.Intents.default()
client = discord.Client(intents=intents)


def load_seen():
    # None means this is the first run and seen.json does not exist yet.
    if not os.path.exists(SEEN_FILE):
        return None
    with open(SEEN_FILE, "r", encoding="utf-8") as file:
        return set(json.load(file))


def save_seen(seen):
    with open(SEEN_FILE, "w", encoding="utf-8") as file:
        json.dump(sorted(seen), file, indent=2)


def job_message(job):
    return (
        f"**{job['company']}** — {job['title']}\n"
        f"{job['location']} | {job['source']}\n"
        f"{job['link']}"
    )


@tasks.loop(hours=1)
async def check_jobs():
    try:
        channel = await client.fetch_channel(int(CHANNEL_ID))
    except (discord.DiscordException, ValueError) as error:
        print("Could not open the channel. Check CHANNEL_ID:", error)
        return

    seen = load_seen()

    # First run: remember current jobs, do not post the old list.
    if seen is None:
        current = jobs.get_new_jobs(set())
        if current is None:
            print("Could not download job lists. Trying again later.")
            return
        save_seen({job["link"] for job in current})
        await channel.send("Watching for new internships.")
        print("Saved the current list. New internships will be posted next time.")
        return

    new_jobs = jobs.get_new_jobs(seen)
    if new_jobs is None:
        print("Could not download job lists. Trying again later.")
        return

    # Test: print how many new jobs we found
    print("New jobs found:", len(new_jobs))

    for job in new_jobs[:MAX_POSTS]:
        await channel.send(job_message(job))
        seen.add(job["link"])

    save_seen(seen)


@check_jobs.before_loop
async def wait_until_ready():
    await client.wait_until_ready()


@client.event
async def on_ready():
    print(f"Logged in as {client.user}")
    if not check_jobs.is_running():
        check_jobs.start()


if TOKEN is None or CHANNEL_ID is None or not CHANNEL_ID.isdigit():
    print("Add DISCORD_TOKEN and CHANNEL_ID to a .env file first.")
else:
    client.run(TOKEN)
