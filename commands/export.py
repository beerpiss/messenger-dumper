import datetime
import os

import aiosqlite


def add_command(subparsers):
    export_parser = subparsers.add_parser(
        "export",
        help="export chat logs to viewer"
    )
    export_parser.add_argument(
        "-i",
        "--id",
        type=int,
        nargs="+",
        required=True,
        help="IDs of threads to export (the long string of number in the chat URL)",
    )
    return export_parser


async def execute(args):
    if not os.path.exists(args.database):
        print("[ERROR] No database file found.")
        exit(1)

    async with aiosqlite.connect(args.database) as conn:
        dump = {
            "meta": {
                "users": {},
                "userindex": [],
                "servers": [{
                    "name": "\u200B",
                    "type": "server"
                }],
                "channels": {},
            },
            "data": {},
        }
        
        for thread_id in args.id:
            str_thread_id = str(thread_id)

            async with conn.execute("SELECT name FROM channels WHERE id = ?", (thread_id,)) as cursor:
                name = (await cursor.fetchone())[0]
            
            dump["meta"]["channels"][str_thread_id] = {
                "server": 0,
                "name": name,
                "nsfw": False,
            }

            async with conn.execute(
                (
                    "SELECT DISTINCT sender_id, name, avatar_url "
                    "FROM messages "
                    "LEFT JOIN users ON messages.sender_id = users.id "
                    "WHERE channel_id = ?"
                ),
                (thread_id,),
            ) as cursor:
                async for user in cursor:
                    id, name, avatar_url = user
                    str_id = str(id)
                    dump["meta"]["userindex"].append(str_id)
                    dump["meta"]["users"][str_id] = {
                        "name": name,
                        "avatar": avatar_url,
                        "tag": "0",
                    }
            
            dump["data"][str_thread_id] = {}
            async with conn.execute(
                (
                    "SELECT id, sender_id, text, timestamp, unsent_timestamp "
                    "FROM messages "
                    "WHERE channel_id = ?"
                ),
                (thread_id,)   
            ) as cursor:
                async for message in cursor:
                    id, sender_id, text, timestamp, _ = message
                    dump["data"][str_thread_id][id] = {
                        "u": dump["meta"]["userindex"].index(str(sender_id)),
                        "t": timestamp,
                        "m": text,
                    }

                    async with conn.execute(
                        (
                            "SELECT name, url, width, height "
                            "FROM attachments ",
                            "WHERE message_id = ?"
                        ),
                        (id,)
                    ) as cursor:
                        async for attachment in cursor:
                            if "a" not in dump["data"][str_thread_id][id]:
                                dump["data"][str_thread_id][id]["a"] = []
                            
                            dumped_attachment = {
                                "url": attachment[1],
                                "name": attachment[0],
                            }
                            if attachment[2]:
                                dumped_attachment["width"] = attachment[2]
                            if attachment[3]:
                                dumped_attachment["height"] = attachment[3]
                            dump["data"][str_thread_id][id]["a"]
                
