import discord
import json
import logging
import os

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


def get_data(ctx: Context) -> dict:
    """
    Get all data corresponding to the context
    :param ctx: Context
    :return: Stored data
    """

    path = f"{get_config('savepath')}{ctx.guild}.json"
    if os.path.isfile(path):
        with open(path, "r") as data_file:
            data = json.load(data_file)

        return data

    # Create the save-file of it does not exist
    with open(path, "w+") as save_file:
        json.dump(dict(), save_file)

    return {}


def write_data(data: dict, ctx: Context):
    """
    Write data to the save-file corresponding to the context
    :param data: data to be saved
    :param ctx: context
    """

    with open(f"{get_config('savepath')}{ctx.guild}.json", "w+") as data_file:
        json.dump(data, data_file)


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
        status = data[key]["Status"]
        if status == "on":
            return "\U0001F7E2"
        elif status == "off":
            return "\U0001F534"
        return "\U000026AA"
    except KeyError:
        return ""


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


ERROR_COLOR = int(get_config("error_color"), 16)
BOT_COLOR = int(get_config("bot_color"), 16)

# Init Logging
logging.basicConfig(filename=get_config("logfile"), level=logging.DEBUG)

with open(get_config("token_file"), "r") as file:
    token = file.read()

client = commands.Bot(command_prefix=get_config("prefix"))


@client.event
async def on_ready():
    """
    Function will be executed once the bot is logged in
    """
    logging.info("Successfully logged in.")
    print("Logged in!")


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
        if field.lower in fields[k]:
            field = k
            break
    else:
        # No match found
        await ctx.send(embed=discord.Embed(description=f"No field named: {field}", color=ERROR_COLOR))
        return

    try:
        data = get_data(ctx)

        if entry not in data:
            await ctx.send(embed=discord.Embed(description=f"No entry named: {entry}", color=ERROR_COLOR))
            return

        logging.info(f"Editing {entry}: {data[entry]}")

        data[entry][field] = tuple_to_string(args)
        write_data(data, ctx)

        logging.info(f"Successfully edited entry {entry}: {data[entry]}")
        await ctx.send(embed=discord.Embed(description=f"Successfully updated the entry: {entry}", color=0x00FF00))
    except Exception as e:
        logging.error(e)
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
            await ctx.send(
                embed=discord.Embed(description=f"No entry named: {name}", color=ERROR_COLOR))
            return

        logging.info(f"Deleting the entry: {data[name]}")

        # Delete the entry from the dict and save the dict to the file
        del data[name]
        write_data(data, ctx)

        await ctx.send(embed=discord.Embed(description=f"Successfully removed the entry: {name}", color=0x00FF00))
    except Exception as e:
        logging.error(e)
        await send_error(ctx)


@client.command(
    name="search",
    aliases=["info", "get"],
    description="Search for an entry to display information",
    help="NAME"
)
async def search(ctx: Context, name: str):
    # TODO: Comments
    try:
        data = get_data(ctx)

        if name not in data:
            suggestions = get_closest(data.keys(), name, 3)
            msg = join_list(suggestions, "\n-")
            await ctx.send(embed=discord.Embed(title=f"No entry named: {name}",
                           description=f"Maybe one of those is what you look for:\n-{msg}", color=0xBBBB00))

            return

        msg = discord.Embed(
            title=name,
            color=BOT_COLOR
        )
        if data[name]["Thumbnail"]:
            msg.set_thumbnail(url=data[name]["Thumbnail"])

        if data[name]["Location"]:
            msg.add_field(name="Location", value=data[name]["Location"], inline=True)
        if data[name]["Direction"]:
            msg.add_field(name="Piston bolt directions", value=data[name]["Direction"], inline=True)
        if data[name]["Rates"]:
            msg.add_field(name="Rates", value=data[name]["Rates"], inline=True)
        if data[name]["Instructions"]:
            msg.add_field(name="Instructions", value=data[name]["Instructions"], inline=False)
        if data[name]["Info"]:
            msg.add_field(name="Extra Information", value=data[name]["Info"], inline=False)
        await ctx.send(embed=msg)

        for img in data[name]["Media"].split(";"):
            if not img:
                continue
            try:
                # m = discord.Embed(description=img)
                # m.set_image(url=img)
                # await ctx.send(embed=m)
                await ctx.send(img)
            except Exception as e:
                logging.error(e)
                await ctx.send(embed=discord.Embed(description=f"Bad Link! {img}", color=0xFF0000))

    except Exception as e:
        logging.error(e)
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
        entry_list = [f"{i}\t{get_status(data, i)}" for i in data.keys()]
        entry_list = join_list(entry_list, "\n")

        await ctx.send(embed=discord.Embed(title="All locations", color=BOT_COLOR, description=entry_list))

    except Exception as e:
        logging.error(e)
        await send_error(ctx)

client.run(token)
