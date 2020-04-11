import mongothon

from dbconnect import my_db


def delete_many(filter):
    my_db['game'].delete_many(filter)


game_schema = mongothon.Schema({
    "server": {"type": int, "required": True},
    "players": {"type": list, "required": True},  # list of villager discord_id
    "inlove": {"type": list, "default": []},
    "bakerdead": {"type": bool, "default": False},
    "voting": {"type": bool, "default": False},
    "last_protected_id": {"type": int, "default": -1},
    "dying_villager_id": {"type": list, "default": []},
    "morning_messages": {"type": list, "default": []},
    "protected": {"type": int, "default": -1},
    "hunter_ids": {"type": list, "default": []},
    "starving": {"type": list, "default": []},
    "werewolfcount": {"type": int, "required": True},
    "villagercount": {"type": int, "required": True},
})

Game = mongothon.create_model(game_schema, my_db['game'])
