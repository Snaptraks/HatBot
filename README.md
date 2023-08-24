# HatBot
Repository for HatBot on the Hatventures Community Discord server.

## Description
HatBot is a custom made Discord bot exclusively for the [Hatventures Community Discord server](https://discord.gg/ByXm745). It provides both entertainement features for all members and moderation tools for the staff.

It has been coded to be as modular as possible, with the possibility to add/remove or enable/disable features as easily as possible.

## Issues
You are welcome and encouraged to create issues here, either for bug fixes or feature requests.

## Contributing
You can help contributing to HatBot by forking the repository and creating pull requests in the `master` branch. Contributions can be in the form of bug fixes, code syntax improvement, or even feature suggestions!

For more details check `CONTRIBUTING.md`.

### License
This repository is provided for education purposes, and community contributions only. Please do not create personal instances of the bot with this code without explicit written permission from me (`snaptraks` on Discord).

### Requirements
Nevertheless, to run the bot you will need Python 3.11+ and the packages from `requirements.txt`.

### Running the bot locally
With all this in mind, to run the bot locally and help with the development, you will need a few things. Assuming your Python environment is correctly set up:

1. [Create a bot account](https://discordpy.readthedocs.io/en/latest/discord.html#creating-a-bot-account).
2. Copy your secret token in a file named `config.py` under `hatbot_token` (see `config.py.example` for more details).
3. [Invite the bot to your server](https://discordpy.readthedocs.io/en/latest/discord.html#inviting-your-bot). I recommend creating a dedicated Discord server for this, so that you are 100% sure to have total control over it.
4. Start the bot with `python HatBot.py` from a terminal (might work with other methods but it has not been tested).
5. Once the bot is on the server, you can enter commands and interact with it. If you modify the code (either the main HatBot.py file or code inside a [Cog](https://discordpy.readthedocs.io/en/latest/ext/commands/cogs.html)), you can stop the bot (Ctrl + C in the terminal) and restart it like in step 4.

### Running inside a Docker container
You can also run the bot inside a Docker container, if you prefer. I have included the necessary files to create your image and start the container, all you need is run the commands inside the project's folder:

```
docker compose up
```

This should take care of creating the necessary images, volumes, and container for the bot to function properl.

If you want to run the bot in detached mode, allowing you to close the terminal once started, you can use the `--detach / -d` flag and have the process run in the background:

```
docker compose up -d
```

The `restart: always` specification in the `docker-compose.yml` file will allow the bot to restart even in the event of a crash.

You can stop the bot with the command `docker compose down` from the project's folder.
