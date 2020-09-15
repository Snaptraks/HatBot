# HatBot
Repository for HatBot on the Hatventures Community Discord server.

## Description
HatBot is a custom made Discord bot exclusively for the [Hatventures Community Discord server](https://discord.gg/ByXm745). It provides both entertainement features for all members and moderation tools for the staff.

It has been coded to be as modular as possible, with the possibility to add/remove or enable/disable features as easily as possible.

## Issues
You are welcome and encouraged to create issues here, either for bug fixes or feature requests.

## Contributing
You can help contributing to HatBot by forking the repository and creating pull requests in the `master` branch. Contributions can be in the form of bug fixes, code syntax improvement, and additions to the lines that HatBot can reply with (like when mentionned for example)

For more details check `CONTRIBUTING.md`.

### License
This repository is provided for education purposes, and community contributions only. Please do not create personal instances of the bot with this code without explicit written permission from me (Snaptraks#2606 on Discord).

### Requirements
Nevertheless, to run the bot you will need Python 3.7+ and the packages from `requirements.txt`.

### Running the bot locally
With all this in mind, to run the bot locally and help with the development, you will need a few things. Assuming your Python environment is correctly set up:

1. [Create a bot account](https://discordpy.readthedocs.io/en/latest/discord.html#creating-a-bot-account).
2. Copy your secret token in a file named `config.py` under `hatbot_token` (see `config.py.example` for more details). The rest of the configuration file is not necessary to run the bot and should not prevent it from running.
3. [Invite the bot to your server](https://discordpy.readthedocs.io/en/latest/discord.html#inviting-your-bot). I recommend creating a dedicated Discord server for this, so that you are 100% sure to have total control over it.
4. Start the bot with `python HatBot.py` from a terminal (might work with other methods but it has not been tested).
5. Once the bot is on the server, you can enter commands and interact with it. If you modify a [Cog](https://discordpy.readthedocs.io/en/latest/ext/commands/cogs.html), you can use:
 * ```!cogs``` to list currently loaded cogs
 * ```!cogs load cogs.Name``` to load a new cog,
 * ```!cogs reload cogs.Name``` to reload an already loaded cog
 * ```!cogs unload cogs.Name``` to remove a cog from the bot

### Running inside a docker container
You can also run the bot inside a docker container, if you prefer. I have included the necessary files to create your image and start the container, all you need is run the commands inside the project's folder:

* (Optional, if you want to move the image to another machine)
```
docker build \
   --file .docker/Dockerfile \
   --tag discordbot \
   .
```
* (Optional, save the image to disk)
```
docker save --output discordbot.tar discordbot
```
* (Optional) Move the image to your prefered machine, as well as the ``.docker/``  subfolder.
* (Optional, on the other machine to load the image there)
```
docker load --input discordbot.tar
```
* [Build the image if not already built and] Start the bot, creating the necessary volumes for the database.
```
docker-compose \
   --project-name hatbot \
   --file .docker/docker-compose.yml \
   --env-file .docker/hatbot/.env \
   up \
   --detatch
```
