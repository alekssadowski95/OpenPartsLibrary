import uuid

import pandas as pd

from openpartslibrary.models import Part
from openpartslibrary.db import create_session


session = create_session()

def print_parts(session):
    parts = session.query(Part).all()
    print('\n')
    print('Parts:')
    print('------')
    for part in parts:
        print(part)
    print('------')

part_1 = Part(uuid=str(uuid.uuid4()), name='Trochoidal milling cutter', number='TRX-230-115')
session.add(part_1)
session.commit()

parts = session.query(Part).all()


engine = session.get_bind()
part_table = pd.read_sql_table(table_name="parts", con=engine)

pd.set_option('display.max_columns', 8)
pd.set_option('display.width', 200)

print(part_table)

from tabulate import tabulate
#print(tabulate(part_table, headers='keys', tablefmt='psql'))
