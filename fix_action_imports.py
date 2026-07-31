def prepend_imports(file_path, imports):
    with open(file_path, 'r') as f:
        content = f.read()
    with open(file_path, 'w') as f:
        f.write(imports + '\n' + content)

prepend_imports('src/tuipet/appactions/care_actions.py', '''
import tuipet.ui.screens.feedscreen as feedscreen
import tuipet.ui.screens.disciplinescreen as disciplinescreen
''')

prepend_imports('src/tuipet/appactions/nav_actions.py', '''
import tuipet.ui.screens.adventurescreen as adventurescreen
import tuipet.ui.screens.backgroundscreen as backgroundscreen
import tuipet.ui.screens.battlescreen as battlescreen
import tuipet.ui.screens.dnascreen as dnascreen
import tuipet.ui.screens.lobbyscreen as lobbyscreen
import tuipet.ui.screens.shopscreen as shopscreen
import tuipet.ui.screens.tournamentscreen as tournamentscreen
''')

prepend_imports('src/tuipet/appactions/system_actions.py', '''
import tuipet.ui.screens.bugscreen as bugscreen
import tuipet.ui.screens.helpscreen as helpscreen
import tuipet.ui.screens.lobbyscreen as lobbyscreen
import tuipet.ui.screens.optionsscreen as optionsscreen
import tuipet.ui.screens.titlescreen as titlescreen
''')
