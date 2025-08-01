from .models import Part


def print_all_users(session):
    users = session.query(Part).all()
    print('\n')
    print('Parts:')
    print('------')
    for user in users:
        print(user)
    print('------')