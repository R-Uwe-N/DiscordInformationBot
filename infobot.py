import discord
import json
import logging
import os

from discord.ext import commands
from discord.ext.commands.context import Context


def get_config(name: str) -> str:
    with open("config.json", "r") as config_file:
        data = json.load(config_file)

    return data[name]


def get_data(ctx: Context) -> dict:
    path = f"{get_config('savepath')}{ctx.guild}.log"
    if os.path.isfile(path):
        with open(path, "r") as data_file:
            data = json.load(data_file)

        return data
    with open(path, "w+") as _:
        pass

    return {}


def write_data(data: dict, ctx: Context):
    with open(f"{get_config('savepath')}{ctx.guild}.log", "w+") as data_file:
        json.dump(data, data_file)


def tuple_to_string(tup: tuple) -> str:
    return " ".join(map(str, tup))


def join_args(alist: list) -> str:
    return "=".join(map(str, alist)).strip()


async def send_error(ctx: Context):
    await ctx.send(embed=discord.Embed(description=f"Something went wrong! :(", color=0xFF0000))


logging.basicConfig(filename=get_config("logfile"), level=logging.DEBUG)

with open("token", "r") as file:
    token = file.read()

client = commands.Bot(
    command_prefix=get_config("prefix")
)


@client.event
async def on_ready():
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
    except:
        await send_error(ctx)


@client.command(
    name="add",
    aliases=["new"],
    description="Add a new entry",
    help="NAME [l/location LOCATION] $ [d/direction DIRECTION] $ [r/rates RATES] $ [i/instructions INSTRUCTIONS] $ "
         "[info EXTRA INFORMATION] $ [t/thumbnail IMAGE_URL] $ [img/images IMAGE_URLS]"
)
async def add(ctx: Context, name: str, *args: str):
    # TODO: Comments
    logging.info(f"Create new entry: {name}")
    new_entry = {"Location": "", "Direction": "", "Rates": "", "Instructions": "", "Info": "", "Images": "",
                 "Thumbnail": ""}

    args = tuple_to_string(args).split("$")

    for arg in args:
        cmd, *param = arg.split("=")
        cmd = cmd.lower().strip()
        param = join_args(param).strip()

        if cmd == "location" or cmd == "l":
            new_entry["Location"] = param
            logging.info(f"Set location field to: {param}")

        elif cmd == "direction" or cmd == "d":
            new_entry["Direction"] = param
            logging.info(f"Set direction field to: {param}")

        elif cmd == "rates" or cmd == "r":
            new_entry["Rates"] = param
            logging.info(f"Set rates field to: {param}")

        elif cmd == "instructions" or cmd == "i":
            new_entry["Instructions"] = param
            logging.info(f"Set instructions field to: {param}")

        elif cmd == "info":
            new_entry["Info"] = param
            logging.info(f"Set info field to: {param}")

        elif cmd == "images" or cmd == "img" or cmd == "image":
            new_entry["Images"] = param
            logging.info(f"Set images field to: {param}")

        elif cmd == "thumbnail" or cmd == "t":
            new_entry["Images"] = param
            logging.info(f"Set images field to: {param}")

        elif cmd == "":
            break

        else:
            logging.info(f"Unknown field name: {cmd}")
            await ctx.send(embed=discord.Embed(description=f"Unknown field name: {cmd}", color=0xFF0000))
            return
    try:
        data = get_data(ctx)

        if name in data:
            await ctx.send(embed=discord.Embed(description=f"The entry {name} already exists! Use "
                                                           f"`{get_config('prefix')}edit {name}` instead.",
                                               color=0xFF0000))
            return

        data[name] = new_entry
        write_data(data, ctx)
        logging.info(f"Successfully saved new entry: {new_entry}")
        await ctx.send(embed=discord.Embed(description="New entry saved!", color=0x00FF00))
    except:
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
    except:
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
            except:
                await ctx.send(embed=discord.Embed(description=f"Bad Link! {img}", color=0xFF0000))

    except:
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

    except:
        await send_error(ctx)

client.run(token)