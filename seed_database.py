import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database_setup import Base, User, Category, Item

engine = create_engine('sqlite:///category.db')
# Bind the engine to the metadata of the Base class so that the
# declaratives can be accessed through a DBSession instance
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
# A DBSession() instance establishes all conversations with the database
# and represents a "staging zone" for all the objects loaded into the
# database session object. Any change made against the objects in the
# session won't be persisted into the database until you call
# session.commit(). If you're not happy about the changes, you can
# revert all of them back to the last commit by calling
# session.rollback()
session = DBSession()


def create_record(seed, seed_type):
    """
    Abstract creation of seed record from the given `dictionary`
    and `seed_type`
    """
    # Create a constructor from the imported User, Category or Item classes
    constructor = globals()[seed_type]
    record = constructor(**seed)
    session.add(record)
    session.commit()


if __name__ == '__main__':
    # Load the `seeds.json` file, and iterate, creating seed records for each
    # type of record.
    with open('seeds.json') as seeds_json:
        seeds = json.load(seeds_json)

        # Use this Array to maintain order of creation
        seed_types = ['User', 'Category', 'Item']

        for seed_type in seed_types:
            for seed in seeds[seed_type]:
                create_record(seed, seed_type)

    print "Seeded User, Category and Item records"
