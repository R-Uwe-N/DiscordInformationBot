import discord
import json
import logging
import os

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


async def send_error(ctx: Context):
    """
    Helper function to send an error message
    :param ctx: Context
    """
    await ctx.send(embed=discord.Embed(description=f"Something went wrong :(", color=int(get_config("error_color"), 16)))


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
    # TODO: Comments
    if field.lower() == "l" or field.lower() == "location":
        field = "Location"
    elif field.lower() == "d" or field.lower() == "direction":
        field = "Direction"
    elif field.lower() == "r" or field.lower() == "rates":
        field = "Rates"
    elif field.lower() == "i" or field.lower() == "instructions":
        field = "Instructions"
    elif field.lower() == "info":
        field = "Info"
    elif field.lower() == "img" or field.lower() == "image" or field.lower() == "images":
        field = "Images"
    elif field.lower() == "t" or field.lower() == "thumbnail":
        field = "Thumbnail"
    else:
        await ctx.send(embed=discord.Embed(description=f"No field named: {field}", color=0xFF0000))

    try:
        data = get_data(ctx)

        if entry not in data:
            await ctx.send(embed=discord.Embed(description=f"No entry named: {entry}", color=0xFF0000))
            return

        if field not in data[entry]:
            await ctx.send(embed=discord.Embed(description=f"No field named: {field}", color=0xFF0000))
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
    # TODO: Comments
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
            await ctx.send(embed=discord.Embed(description=f"Unknown field name: {cmd}",
                                               color=int(get_config("error_color"), 16)))
            return
    try:
        data = get_data(ctx)

        if name in data:
            await ctx.send(
                embed=discord.Embed(
                    description=f"The entry {name} already exists! Use `{get_config('prefix')}edit {name}` instead.",
                    color=int(get_config("error_color"), 16)
                ))
            return

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
    # TODO Comments
    try:
        data = get_data(ctx)

        if name not in data:
            await ctx.send(embed=discord.Embed(description=f"No entry named: {name}", color=0xFF0000))
            return

        logging.info(f"Deleting the entry: {data[name]}")

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
            # TODO suggest closest
            await ctx.send(embed=discord.Embed(description=f"No entry named: {name}", color=0xFF0000))

        msg = discord.Embed(
            title=name,
            color=0x009999
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

        for img in data[name]["Images"].split(" "):
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
    # TODO: Comments
    try:
        data = get_data(ctx).keys()

        # Maybe use embeds for each entry to show the thumbnail
        msg = discord.Embed(
            title="All locations",
            color=0x009999,
            description="\n".join(data)
        )

        await ctx.send(embed=msg)

    except Exception as e:
        logging.error(e)
        await send_error(ctx)

client.run(token)
