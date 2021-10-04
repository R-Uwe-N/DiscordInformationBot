import discord
import json
import logging
import os

import discord.ext.commands.errors as errors

from difflib import SequenceMatcher
from discord.ext import commands
from discord.ext.commands.context import Context


def get_config(name: str) -> str:
    """
    Read a parameter from the config file
    :param name: parameter_name
    :return: value of the parameter
    """

    with open("config.json", "r") as config_file:
        data = json.load(config_file)

    return data[name]


def get_fields() -> dict:
    """
    Function to load and return the fields-config-file
    """

    with open("input_fields.json", "r") as json_file:
        data = json.load(json_file)

    return data


def get_data(ctx: Context, backup=False) -> dict:
    """
    Get all data corresponding to the context
    :param ctx: Context of the request
    :param backup: Defines whether the previous save should be loaded
    :return: Stored data
    """

    path = f"{get_config('savepath')}{ctx.guild}.json"
    backup_path = f"{get_config('savepath')}{ctx.guild}{ctx.guild.id}.json"

    if backup and os.path.isfile(path):
        path = backup_path

    if os.path.isfile(path):
        with open(path, "r") as data_file:
            data = json.load(data_file)

        return data

    # Create the save-file of it does not exist
    with open(path, "w+") as save_file:
        json.dump(dict(), save_file)

    with open(backup_path, "w+") as save_file:
        json.dump(dict(), save_file)

    return {}


def write_data(data: dict, ctx: Context):
    """
    Write data to the save-file corresponding to the context
    :param data: data to be saved
    :param ctx: context
    """

    path = f"{get_config('savepath')}{ctx.guild}.json"
    backup_path = f"{get_config('savepath')}{ctx.guild}{ctx.guild.id}.json"

    backup = get_data(ctx)

    with open(path, "w") as data_file:
        json.dump(data, data_file)

    with open(backup_path, "w") as data_file:
        json.dump(backup, data_file)


def tuple_to_string(tup: tuple) -> str:
    """
    Helper function to convert a tuple to a string
    :param tup: Tuple containing information
    :return: Concatenated string
    """
    return " ".join(map(str, tup))


def join_list(alist: list, insert: str) -> str:
    """
    Helper function to concatenate a list
    :param alist: List containing strings
    :param insert: Insert between each string of the list
    :return: Concatenated string
    """
    return insert.join(map(str, alist)).strip()


def get_status(data: dict, key: str) -> str:
    """
    Helper function to parse the status of an entry and return a corresponding emoji
    :param data: Dict containing multiple entries
    :param key: Key for the correct entry
    :return: Emoji corresponding to the status of the given entry
    """
    try:
        stat = data[key]["Status"]
        if stat == "on":
            return "\U0001F7E2"
        elif stat == "off":
            return "\U0001F534"
        return "\U000026AA"
    except KeyError:
        return ""


def set_status(ctx: Context, name: str, new_status: str) -> bool:
    """
    Helper function to set the status of an entry
    :param ctx: Context of the request
    :param name: Name of the entry to be changed
    :param new_status: New status of the entry
    :return: Whether the change was successful or not
    """

    data = get_data(ctx)

    # Check if the specified entry exists
    if name not in data:
        return False

    # Set status and save to file
    data[name]["Status"] = new_status

    write_data(data, ctx)
    return True


def get_closest(data: list, pattern: str, num=3) -> list:
    """
    Helper function to find the closest matches to the given pattern in data

    :param data: list containing strings for comparison
    :param pattern: Pattern to be matched
    :param num: Amount of matches returned
    return list of the closest matches to the pattern in data
    """
    results = []
    for d in data:
        p = SequenceMatcher(d, pattern).ratio()
        results.append([p, d])

    results.sort(key=lambda x: x[0])

    if len(results) <= num:
        return [i[1] for i in results]

    return [results[i][1] for i in range(num)]


async def send_error(ctx: Context):
    """
    Helper function to send an error message
    :param ctx: Context
    """
    await ctx.send(
        embed=discord.Embed(description=f"Something went wrong! :(", color=ERROR_COLOR))


async def send_not_found(ctx: Context, value: str):
    """
    Helper function to send a not found message
    :param ctx: Context of the request
    :param value: The thing which did not get found
    """
    await ctx.send(embed=discord.Embed(description=f"No entry named: {value}", color=ERROR_COLOR))


ERROR_COLOR = int(get_config("error_color"), 16)
BOT_COLOR = int(get_config("bot_color"), 16)

# Init Logging
logging.basicConfig(filename=get_config("logfile"), level=logging.DEBUG)

with open(get_config("token_file"), "r") as file:
    token = file.read()

client = commands.Bot(command_prefix=get_config("prefix"))


# TODO make better help strings

@client.event
async def on_ready():
    """
    Function will be executed once the bot is logged in
    """
    logging.info("Successfully logged in.")
    print("Logged in!")

    await client.change_presence(activity=discord.Activity(type=discord.ActivityType.listening,
                                                           name=f" {get_config('prefix')}help"))


@client.command(
    name="edit",
    description="Edit a specific field of an existing entry",
    help="ENTRY FIELD TEXT"
)
async def edit(ctx: Context, entry: str, field: str, *args: str):
    """
    Command edit: Edit a specified field of an existing entry using the given arguments
    :param ctx: The context of the request
    :param entry: The name of the entry to be edited
    :param field: The name of the field to be edited
    :param args: The new value
    """
    
    # Get correct field key
    fields = get_fields()
    for k in fields.keys():
        if field.lower() in [x.lower() for x in fields[k]]:
            field = k
            break
    else:
        # No match found
        await ctx.send(embed=discord.Embed(description=f"No field named: {field}", color=ERROR_COLOR))
        return

    try:
        data = get_data(ctx)

        if entry not in data:
            await send_not_found(ctx, entry)
            return

        logging.info(f"Editing {entry}: {data[entry]}")

        data[entry][field] = tuple_to_string(args)
        write_data(data, ctx)

        logging.info(f"Successfully edited entry {entry}: {data[entry]}")
        await ctx.send(embed=discord.Embed(description=f"Successfully updated the entry: {entry}", color=0x00FF00))
    except Exception as e:
        logging.error(e)
        await send_error(ctx)


@edit.error
async def edit_error(ctx: Context, error):
    """
    Error handling for function edit
    :param ctx: Context of the request
    :param error: Error type
    """
    if isinstance(error, errors.MissingRequiredArgument):
        await ctx.send(embed=discord.Embed(
            description=f"Missing argument! Usage: {get_config('prefix')}edit ENTRY_NAME FIELD_NAME VALUE",
            color=ERROR_COLOR))
    else:
        await send_error(ctx)


@client.command(
    name="add",
    aliases=["new", "create"],
    description="Add a new entry",
    help="NAME [l/location LOCATION] $ [d/direction DIRECTION] $ [r/rates RATES] $ [i/instructions INSTRUCTIONS] $ "
         "[info EXTRA INFORMATION] $ [t/thumbnail IMAGE_URL] $ [images/video/gallery/link URL; URL; ...]"
)
async def add(ctx: Context, name: str, *args: str):
    """
    Command Add: Creates a new entry with the given parameters and saves it to a file
    :param ctx: Context of the request
    :param name: Name of the new entry
    :param args: Arguments for the new entry
    """

    logging.info(f"Create new entry: {name}")

    # Load the possible arguments
    fields = get_fields()

    # Get the keys from the json_file and create a new dict
    new_entry = dict.fromkeys(fields.keys(), "")

    args = tuple_to_string(args).split("$")

    for arg in args:
        # Parse argument ot get the command and the corresponding parameter
        cmd, *param = arg.split("=")
        cmd = cmd.lower().strip()
        param = join_list(param, "=").strip()  # rejoin the parameter list to make it possible to have = contained

        # Create the entry also if no parameters are given
        if cmd == "":
            continue

        # Iterate over the possible fields
        for k in fields.keys():
            # Check if the cmd is valid
            if cmd in fields[k]:
                new_entry[k] = param
                logging.info(f"Set {k} field to: {param}")
                break
        else:
            # No match found -> print error message and not create the entry
            logging.info(f"Unknown field name: {cmd}")
            await ctx.send(embed=discord.Embed(description=f"Unknown field name: {cmd}", color=ERROR_COLOR))
            return
    try:
        data = get_data(ctx)

        # Check if the entry already exists
        if name in data:
            await ctx.send(
                embed=discord.Embed(
                    description=f"The entry {name} already exists! Use `{get_config('prefix')}edit {name}` instead.",
                    color=ERROR_COLOR
                ))
            return

        # Save entry to file
        data[name] = new_entry
        write_data(data, ctx)

        logging.info(f"Successfully saved new entry: {new_entry}")
        await ctx.send(embed=discord.Embed(description="New entry saved!", color=0x00FF00))
    except Exception as e:
        logging.error(e)
        await send_error(ctx)


@add.error
async def add_error(ctx: Context, error):
    """
    Error handling for function add
    :param ctx: Context of the request
    :param error: Error type
    """
    if isinstance(error, errors.MissingRequiredArgument):
        await ctx.send(embed=discord.Embed(
            description=f"Missing argument! Usage: {get_config('prefix')}add ENTRY_NAME FIELD=VALUE $ FIELD=VALUE ...",
            color=ERROR_COLOR))
    else:
        await send_error(ctx)


@client.command(
    name="delete",
    aliases=["remove"],
    description="Remove an existing entry",
    help="NAME"
)
async def delete(ctx: Context, name: str):
    """
    Command delete: Removes the entry with the specified name from the stored entries
    :param ctx: Context of the request
    :param name: Name of the entry to be deleted
    """

    try:
        data = get_data(ctx)

        # Check if the entry exists
        if name not in data:
            await send_not_found(ctx, name)
            return

        logging.info(f"Deleting the entry: {data[name]}")

        # Delete the entry from the dict and save the dict to the file
        del data[name]
        write_data(data, ctx)

        await ctx.send(embed=discord.Embed(description=f"Successfully removed the entry: {name}", color=0x00FF00))
    except Exception as e:
        logging.error(e)
        await send_error(ctx)


@delete.error
async def delete_error(ctx: Context, error):
    """
    Error handling for function delete
    :param ctx: Context of the request
    :param error: Error type
    """
    if isinstance(error, errors.MissingRequiredArgument):
        await ctx.send(embed=discord.Embed(
            description=f"Missing argument! Usage: {get_config('prefix')}delete ENTRY_NAME", color=ERROR_COLOR))
    else:
        await send_error(ctx)


@client.command(
    name="info",
    aliases=["search", "get"],
    description="Search for an entry to display information",
    help="NAME"
)
async def search(ctx: Context, name: str):
    """
    Command search: Searches for an entry and displays it's information. In case no match is found some suggestions are
    displayed
    :param ctx: Context of the request
    :param name: Name of the entry to be found
    """
    try:
        data = get_data(ctx)

        if name not in data:
            # Suggest some other entries that are similar to the searched name
            suggestions = get_closest(list(data.keys()), name, 3)
            msg = join_list(suggestions, "\n-")
            await ctx.send(embed=discord.Embed(title=f"No entry named: {name}",
                           description=f"Maybe one of those is what you look for:\n-{msg}", color=0xBBBB00))

            return

        msg = discord.Embed(
            title=name,
            color=BOT_COLOR
        )

        # Set default fields if they have a value
        if data[name]["Thumbnail"]:
            msg.set_thumbnail(url=data[name]["Thumbnail"])

        if data[name]["Location"]:
            msg.add_field(name="Location", value=data[name]["Location"], inline=False)
        if data[name]["Direction"]:
            msg.add_field(name="Piston bolt directions", value=data[name]["Direction"], inline=False)
        if data[name]["Rates"]:
            msg.add_field(name="Rates", value=data[name]["Rates"], inline=False)
        if data[name]["Instructions"]:
            msg.add_field(name="Instructions", value=data[name]["Instructions"], inline=False)
        if data[name]["Info"]:
            msg.add_field(name="Extra Information", value=data[name]["Info"], inline=False)

        # Set any additional field
        fields = get_fields()
        for k in fields:
            # Filter out the default fields
            if k not in ["Thumbnail", "Location", "Direction", "Rates", "Instructions", "Info", "Media", "Status"]:
                if data[name][k]:
                    msg.add_field(name=k, value=data[name][k], inline=False)

        if data[name]["Media"]:
            media = data[name]["Media"].split(";")  # Get individual urls
            try:
                m = ""
                for x in media:
                    if x:
                        x = x.strip().split(" ")  # Split Link name and url
                        if len(x) > 2 or len(x) < 1:  # Filter out invalid format
                            continue
                        elif len(x) == 1:  # Only url with no name
                            m += f"{x}\t"
                        else:  # Format url with the name: [name](url)
                            m += f"[{x[0].strip()}]({x[1].strip()})\t"
                msg.add_field(name="Media", value=m, inline=False)
            except Exception as e:
                logging.error(e)

        await ctx.send(embed=msg)

    except Exception as e:
        logging.error(e)
        await send_error(ctx)


@search.error
async def search_error(ctx: Context, error):
    """
    Error handling for function search
    :param ctx: Context of the request
    :param error: Error type
    """
    if isinstance(error, errors.MissingRequiredArgument):
        await ctx.send(embed=discord.Embed(
            description=f"Missing argument! Usage: {get_config('prefix')}info ENTRY_NAME", color=ERROR_COLOR))
    else:
        await send_error(ctx)


@client.command(
    name="list",
    aliases=["all"],
    description="List the names of all entries",
    help=""
)
async def list_all(ctx: Context):
    """
    Command list: Creates a list of all entry names and displays it
    :param ctx: Context of the request
    """
    try:
        data = get_data(ctx)

        # Create a list of all locations and their status, then concatenate the list to a single string
        entry_list = [f"{get_status(data, i)}\t{i}" for i in data.keys()]
        entry_list = join_list(entry_list, "\n")

        await ctx.send(embed=discord.Embed(title="All locations", color=BOT_COLOR, description=entry_list))

    except Exception as e:
        logging.error(e)
        await send_error(ctx)


@client.command(
    name="media_add",
    aliases=["image_add", "add_media", "add_image", "add_link", "link_add"],
    description="Adds an URL to the Media field",
    help=""
)
async def media_add(ctx: Context, name: str, display: str, url: str):
    """
    Command media_add: Adds an url and a display name to an entry
    :param ctx: Context of the request
    :param name: Name of the entry
    :param display: String which will be displayed as a link
    :param url: link to the media
    """
    try:
        data = get_data(ctx)

        if name not in data:
            await send_not_found(ctx, name)

        # Add new link to the end of existing media
        data[name]["Media"] += f";{display} {url}"

        write_data(data, ctx)

        await ctx.send(embed=discord.Embed(description=f"Successfully added link to {name}", color=0x00FF00))

    except Exception as e:
        logging.error(e)
        await send_error(ctx)


@media_add.error
async def media_add_error(ctx: Context, error):
    """
    Error handling for function media_add
    :param ctx: Context of the request
    :param error: Error type
    """
    if isinstance(error, errors.MissingRequiredArgument):
        await ctx.send(embed=discord.Embed(
            description=f"Missing argument! Usage: {get_config('prefix')}media_add ENTRY_NAME LINK_NAME URL",
            color=ERROR_COLOR))
    else:
        await send_error(ctx)


@client.command(
    name="status",
    aliases=["state"],
    description="Get information what the status of an entry is",
    help=""
)
async def status(ctx: Context, name: str):
    """"
    Function to get and display the status of an entry
    :param ctx: Context of the request
    :param name: Name of the entry
    """
    try:
        data = get_data(ctx)

        # Check if the entry exists
        if name not in data:
            await send_not_found(ctx, name)
            return

        # Get status emoji
        state = get_status(data, name)

        # Construct message
        msg = f"{state} {name}'s status is currently "

        if state == "\U0001F7E2":
            msg += "active!"
        elif state == "\U0001F534":
            msg += "inactive!"
        else:
            msg += "undefined!"

        await ctx.send(embed=discord.Embed(description=msg, color=BOT_COLOR))

    except Exception as e:
        logging.error(e)
        await send_error(ctx)


@status.error
async def status_error(ctx: Context, error):
    """
    Error handling for function status
    :param ctx: Context of the request
    :param error: Error type
    """
    if isinstance(error, errors.MissingRequiredArgument):
        await ctx.send(embed=discord.Embed(
            description=f"Missing argument! Usage: {get_config('prefix')}status ENTRY_NAME", color=ERROR_COLOR))
    else:
        await send_error(ctx)


@client.command(
    name="undo",
    aliases=["redo", "revert"],
    description="Undo the last change made. Note: Only the very last change is revertible",
    help=""
)
async def undo(ctx: Context):
    """
    Command undo: Reverts the effect of the last command which has changed data
    :param ctx: Context of the request
    """
    try:
        # Load the data before the last change
        backup_data = get_data(ctx, backup=True)

        # Write back the data
        write_data(backup_data, ctx)

        # Implementation wor write data allows for redo by just executing undo twice

        await ctx.send(embed=discord.Embed(description="Successfully reverted the last command!", color=0x00FF00))

    except Exception as e:
        logging.error(e)
        await send_error(ctx)


@client.command(
    name="on",
    aliases=["activate", "active"],
    description="Set the state of an entry to active",
    help=""
)
async def on(ctx: Context, name: str):
    """
    Command on: Sets the status of the specified entry to on/active
    :param ctx: Context of the request
    :param name: Name of the entry to be changed
    """
    try:
        if not set_status(ctx, name, "on"):
            await send_not_found(ctx, name)
            return

        await ctx.send(embed=discord.Embed(description=f"Successfully set status of {name} to active", color=0x00FF00))

    except Exception as e:
        logging.error(e)
        await send_error(ctx)


@on.error
async def on_error(ctx: Context, error):
    """
    Error handling for function on
    :param ctx: Context of the request
    :param error: Error type
    """
    if isinstance(error, errors.MissingRequiredArgument):
        await ctx.send(embed=discord.Embed(
            description=f"Missing argument! Usage: {get_config('prefix')}on ENTRY_NAME", color=ERROR_COLOR))
    else:
        await send_error(ctx)


@client.command(
    name="off",
    aliases=["inactivate", "inactive"],
    description="Set the state of an entry to inactive",
    help=""
)
async def off(ctx: Context, name: str):
    """
    Command off: Sets the status of the specified entry to off/inactive
    :param ctx: Context of the request
    :param name: Name of the entry to be changed
    """
    try:
        if not set_status(ctx, name, "off"):
            await send_not_found(ctx, name)
            return

        await ctx.send(embed=discord.Embed(description=f"Successfully set status of {name} to inactive",
                                           color=0x00FF00))

    except Exception as e:
        logging.error(e)
        await send_error(ctx)


@off.error
async def off_error(ctx: Context, error):
    """
    Error handling for function off
    :param ctx: Context of the request
    :param error: Error type
    """
    if isinstance(error, errors.MissingRequiredArgument):
        await ctx.send(embed=discord.Embed(
            description=f"Missing argument! Usage: {get_config('prefix')}off ENTRY_NAME", color=ERROR_COLOR))
    else:
        await send_error(ctx)


@client.command(
    name="no_status",
    aliases=["delete_status", "rm_status", "remove_status", "del_status"],
    description="Removes the status of an entry",
    help=""
)
async def del_status(ctx: Context, name: str):
    """
    Command del_status: Removes the status of an entry
    :param ctx: Context of the request
    :param name: Name of the entry to be changed
    """
    try:
        if not set_status(ctx, name, ""):
            await send_not_found(ctx, name)
            return

        await ctx.send(embed=discord.Embed(description=f"Successfully removed the status of {name}.", color=0x00FF00))

    except Exception as e:
        logging.error(e)
        await send_error(ctx)


@del_status.error
async def del_status_error(ctx: Context, error):
    """
    Error handling for function del_status
    :param ctx: Context of the request
    :param error: Error type
    """
    if isinstance(error, errors.MissingRequiredArgument):
        await ctx.send(embed=discord.Embed(
            description=f"Missing argument! Usage: {get_config('prefix')}no_status ENTRY_NAME", color=ERROR_COLOR))
    else:
        await send_error(ctx)


client.run(token)
