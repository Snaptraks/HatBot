# HatBot
Repository for HatBot on the Hatventures Community Discord server.

## Description
HatBot is a custom made Discord bot exclusively for the [Hatventures Community Discord server](https://discord.gg/ByXm745). It provides both entertainement features for all members and moderation tools for the staff.

It has been coded to be as modular as possible, with the possibility to add/remove or enable/disable features as easily as possible.

## Issues
You are welcome and encouraged to create issues here, either for bug fixes or feature requests.

## Contributing
You can help contributing to HatBot by forking the repository and creating pull requests in the `dev` branch. Contributions can be in the form of bug fixes, code syntax improvement, and additions to the lines that HatBot can reply with (like when mentionned for example)

For more details check `CONTRIBUTING.md`.

### License
This repository is provided for education purposes, and community contributions only. Please do not create personal instances of the bot with this code without explicit written permission from me (Snaptraks#2606 on Discord).

### Requirements
Nevertheless, to run the bot you will need Python 3.7.3 (anything up from 3.5 should work, but all is tested with 3.7.3) and the packages from `requirements.txt`.

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
