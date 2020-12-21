#!/bin/bash

# Sync with GitHub repo
git fetch
git reset --hard
git pull origin master

# Start the bot
python HatBot.py
