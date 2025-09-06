class PartsLibraryCLI:
    def __init__(self):
        ''' CLI to be moved to its own object OpenPartsLibraryCLI in cli.py
        '''
        '''
        command_history = []
        while True:    
            os.system('cls')
            print('************************************************************') 
            print('*  OpenPartsLibrary                                        *')
            print('*  Aleksander Sadowski,  Nandana Gopala Krishnan (C) 2025  *')
            print('************************************************************') 
            pl.display()
            commands = 'add part', 'add supplier', 'modify part', 'modify supplier', 'remove part', 'remove supplier'
            commands_str = ''
            for command in commands:
                commands_str = commands_str + '[' + str(command) + '] '
            print('Commands: ' + commands_str)
            print('Last commands:' + str([command for command in command_history][-5:]))
            input_cmd = input('Enter command: ')
            command_history.append(input_cmd)
            if input_cmd in commands:
                if input_cmd == 'add part':
                    pass
                if input_cmd == 'add supplier':
                    pass
                if input_cmd == 'modify part':
                    os.system('cls')
                    print('************************************************************') 
                    print('*  OpenPartsLibrary                                        *')
                    print('*  Aleksander Sadowski,  Nandana Gopala Krishnan (C) 2025  *')
                    print('************************************************************')
                    pl.display_parts()
                    selected_part = int(input('Enter part id: '))
                    pass
                if input_cmd == 'modify supplier':
                    os.system('cls')
                    print('************************************************************') 
                    print('*  OpenPartsLibrary                                        *')
                    print('*  Aleksander Sadowski,  Nandana Gopala Krishnan (C) 2025  *')
                    print('************************************************************')
                    print()
                    pl.display_suppliers()
                    selected_part = int(input('Enter supplier id: '))
                    pass
                if input_cmd == 'remove part':
                    pass
                if input_cmd == 'remove supplier':
                    pass
        '''
        pass