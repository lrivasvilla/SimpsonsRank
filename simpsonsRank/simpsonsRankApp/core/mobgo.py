from pymongo import mongo_client


def get_db():
    return mongo_client["simpsonsRank"]
