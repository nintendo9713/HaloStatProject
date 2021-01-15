import os
import glob
import re
from operator import itemgetter
import datetime
import numpy as np    
import ast
import calendar

# Probably should leave this false if running recreationally
debug = True

# If set to true, a new __master_sorted_data.txt file will be written from available _raw_data.txt files
update_master_list = False

# If set to true, stats will output to <gamertag>_stats.txt in addition to the screen
write_to_file_enabled = True

# Enter 1 or more gamertags as a string list
gamertag = ["Agnt 007","XiT x007x"]
# If doing a head to head, populate with all gamertags
# @NOTE - Head to Head ™ currently assumes it's ranked games played with - to compare k/d
# @TODO - Map specific .... Win Rate with H2H ™ ...
# @NOTE - These tags don't need a local repo copy...
vs_gamertag = ["Kojangie"]
# ["HpD ScOpEd", "Zim Zim Zim Zim", "Leviathan II", "Southern Slayer"]
# ["Agnt 007","XiT x007x"]
# ["B1oodshed", "Ra1nfall", "HpD Wraith"]
# ["Zer0 X910", "HpD NoScoPeD", "zEr0 4 liFe", "Phoenix VII", "xAznsAreSoSicKx"]
# ["moj4do"] ["Kojangie"]

'''
## DEBUG ## - Currently Testing / Figuring out best way to handle
if not gamertag:
    gamertag.append("__master_sorted_data.txt")
#else:
#    gamertag[0] += "_raw_data.txt"
## DEBUG ## \end   
'''

''' Must Complete - path to data files'''
root_directory = "C:\\Users\\Jesse\\Documents\\Halo2StatsData\\__data\\"

if not gamertag:
    while True:
        gt = input("No gamertag hardcoded.  Enter now: ")
        if len(gt) > 15:
            print("Probably not a gamertag, too long.  Try again.\n\n.")
        if not gt.isalnum():
            print("Should be Alpha/Numeric characters only. Try again.\n\n")
        else:
            gamertag.append(gt)
            break
            
# If you want a copy saved locally, then make sure to enable above (default = enabled)
if write_to_file_enabled is True:
    if gamertag:
        # It will output to a file named after the first gamertag 
        output_file_name = root_directory + gamertag[0] + "_stats.txt"
        output_file = open(output_file_name, "w")
        for gt in gamertag:
            # Writes the URLs for each gamertag at the top of the file
            output_file.write("https://halo.bungie.net/stats/PlayerStatsHalo2.aspx?player=" + gt + "\n")


                
# Player K/D/A's for specific game categories.  If you think of more, AIM me @dane_cook_89
player_stats_global         = np.zeros((3,), dtype=int)
player_stats_customs        = np.zeros((3,), dtype=int)
player_stats_ranked         = np.zeros((3,), dtype=int)
player_stats_clan           = np.zeros((3,), dtype=int)
player_stats_ranked_no_clan = np.zeros((3,), dtype=int)
player_stats_ranked_ffa     = np.zeros((3,), dtype=int)
player_stats_ranked_team    = np.zeros((3,), dtype=int)
player_stats_matchmaking    = np.zeros((3,), dtype=int)

# Head to Head ™ Beta...
head_to_head_player   = np.zeros((3,), dtype=int)
head_to_head_opponent = np.zeros((3,), dtype=int)
head_to_head_games = 0

# (wins, losses, rate)
ranked_win_rate = (np.zeros((3,), dtype = float))



## DEBUG ##
# K / A / D  , then 4th slot is reserved for K/D, and final is ames played in total
player_stats_9_11 = np.zeros((5,), dtype=float)
## DEBUG ## \end

# This is the list that will populate with game structures from the raw data files generated    
global_stats = []

## DEBUG ##
# List of 'source' players the stats master list is taken from
players = []
## DEBUG ## \end

# List of official teams to check against - & yes - if somebody has this as a gamertag, it might break this entire operation
team_list = ['Red Team','Blue Team','Green Team','Yellow Team','Orange Team','Purple Team','Pink Team','Brown Team']

# Keep highest rank and the associated game_id
max_rank_overall = [0, 0]
max_rank_no_clan = [0, 0]

# Stolen from Stack Overflow
# Converts dictionary to string
# @TODO - add formatting - left / right justify & New line fix in file output
def dict_to_string(d):
  return str(d).replace(', ','\n\r').replace("u'","").replace("'","")[1:-1]

# Stolen from Stack Overflow
# Returns key with max value in a dictionary
def key_with_max_value(d):
     v = list(d.values())
     k = list(d.keys())
     return k[v.index(max(v))]

# Husker's famous dictionary insert. All rights reserved by him.
def dictionary_insert(key, dictionary):
    if key in dictionary:
        # Increment count of word by 1 
        dictionary[key] = dictionary[key] + 1
    else:
        # Add the word to dictionary with count 1 
        dictionary[key] = 1

# My horrible manual way of adding 2 hours for PST - CST and adjusting AM / PM
def adjust_time(time):
    # Get the hour as an integer
    hour = int(time.split(':')[0])
    # AM --> PM --> AM
    if hour in ['10','11']:
        if time.split()[1] == 'PM':
            time = time.split()[0] + ' AM ' + time.split()[2]
        else:
            time = time.split()[0] + ' PM ' + time.split()[2]
        #print("#2.5 - " + time)
    
    # Move ahead 2 hours
    hour = hour + 2
    # Adjust hours
    if hour > 12:
        hour -= 12
    # For single digit hours, append a space before it to maintain a clean dictionary
    if hour < 10:
        hour = ' ' + str(hour)
    # Rebuild string
    time = str(hour) + ':' + time.split(':')[1]

    # Concatenate the hour and AM/PM
    time = time.split(':')[0] + " " + time.split()[1]
    
    return time

      
# Used for a time dictionary - number of games played at certain hours
# @TODO - fix dict output and remove unnecessary logic for adding a space before. it's gross.
def init_clock_dictionary():
    return {\
        ' 1 AM': 0, \
        ' 2 AM': 0, \
        ' 3 AM': 0, \
        ' 4 AM': 0, \
        ' 5 AM': 0, \
        ' 6 AM': 0, \
        ' 7 AM': 0, \
        ' 8 AM': 0, \
        ' 9 AM': 0, \
        '10 AM': 0, \
        '11 AM': 0, \
        '12 PM': 0, \
        ' 1 PM': 0, \
        ' 2 PM': 0, \
        ' 3 PM': 0, \
        ' 4 PM': 0, \
        ' 5 PM': 0, \
        ' 6 PM': 0, \
        ' 7 PM': 0, \
        ' 8 PM': 0, \
        ' 9 PM': 0, \
        '10 PM': 0, \
        '11 PM': 0, \
        '12 AM': 0, \
        }

# Used for a weekday dictionary - number of games played at certain hours
def init_weekday_dictionary():
    return {\
        'Sunday': 0, \
        'Monday': 0, \
        'Tuesday': 0, \
        'Wednesday': 0, \
        'Thursday': 0, \
        'Friday': 0, \
        'Saturday': 0, \
        }
        
def init_team_color_dictionary():
    return {\
        'Red Team': 0, \
        'Blue Team': 0, \
        'Green Team': 0, \
        'Yellow Team': 0, \
        'Pink Team': 0, \
        'Brown Team': 0, \
        'Purple Team': 0, \
        'Orange Team': 0, \
        }
        
def init_month_dictionary():
    return {\
        'January': np.zeros((4,), dtype=float), \
        'February': np.zeros((4,), dtype=float), \
        'March': np.zeros((4,), dtype=float), \
        'April': np.zeros((4,), dtype=float), \
        'May': np.zeros((4,), dtype=float), \
        'June': np.zeros((4,), dtype=float), \
        'July': np.zeros((4,), dtype=float), \
        'August': np.zeros((4,), dtype=float), \
        'September': np.zeros((4,), dtype=float), \
        'October': np.zeros((4,), dtype=float), \
        'November': np.zeros((4,), dtype=float), \
        'December': np.zeros((4,), dtype=float), \
        }


def output_stat(s):
    # Comment out for easier debugging
    
    print(s)
    # Write to file if enabled
    if write_to_file_enabled is True:
        output_file.write(s + '\n')
    
        
        
''' Global Counters / Data Aggregators '''
# Create an empty dictionary 
map_dictionary = dict() 
map_kd_dictionary = dict()
date_dictionary = dict() 
time_dictionary = init_clock_dictionary()
weekday_dictionary = init_weekday_dictionary()
game_type_dictionary = dict()
playlist_dictionary = dict()
team_color_customs_dictionary = init_team_color_dictionary()
team_color_ranked_dictionary = init_team_color_dictionary()
team_color_dictionary = init_team_color_dictionary()
clans_dictionary = dict()

## DEBUG ##
monthly_kda_dictionary = init_month_dictionary()
## DEBUG ## \end

# The big one....every player played with counted
player_dictionary = dict()

# Specific Game Counters
ranked_games = 0
ranked_team_games = 0
ranked_ffa_games = 0
unranked_games = 0
unranked_team_games = 0
unranked_ffa_games = 0
custom_games = 0
custom_team_games = 0
custom_ffa_games = 0
clanmatch_games = 0
clanmatch_games_minor = 0
clanmatch_games_major = 0



def process_carnage_report(carnage_report, playlist, is_ranked):

    ''' Build a uniform carnage report '''
    
    # There are 7 types of games:
    #   [1] - Clan Match
    #   [2] - Matchmaking Ranked Team
    #   [3] - Matchmaking Unranked Team
    #   [4] - Matchmaking Ranked Free-for-All
    #   [5] - Matchmaking Unranked Free-for-All
    #   [6] - Custom Team Game
    #   [7] - Custom Free-for-All
    #
    #  The <header>, aka top row, is always:
    #
    #        ['Players', 'Kills', 'Assists', 'Deaths', 'K/D Spread', 'Suicides', 'Betrayals', 'Score']
    #
    #  This works fine in unranked, as all <player> rows perfectly represent this.  You can reshape the list into an 8 wide array as such:
    #    
    #      np.array(carnage_report).reshape(int(len(carnage_report)/8),8)
    #
    #  For an unranked team game, there will also be an 8 element wide row for each team, such as 'Red Team' or 'Blue Team'.  This is why a list of all teams 
    #    are available to check against.  If it is the team row, until you hit another team row, every player beneath is on that.
    #
    #  If a game is ranked - the header is the same, but now all player rows have the following fields:
    #
    #        ['Players', 'Rank', 'Kills', 'Assists', 'Deaths', 'K/D Spread', 'Suicides', 'Betrayals', 'Score']
    #  
    #  Rank will be a # from 1 to 50.  This algorithm makes every carnage report into a 9 element wide row.  The header is easily done with a ".insert(1, 'Rank').
    #    
    #  In an unranked game, you can easily iterate through the list and at every 9 elements, insert a '-'.  Simply a placeholder to disregard.  This is done for
    #    both Team and Free-for-All unranked games.
    #
    #  For a ranked game - either Team or Free-for-All, simply inserting 'Rank' at index [1] is sufficient to create the 9 element wide carnage report since each 
    #    player will already have an actual number as a rank in that element.
    #
    #  The same logic for 'Red Team' / 'Blue Team' (checking against a list) applies for both Ranked and Unranked, as a rank does not appear in a Team row, but you
    #    can't blindly enter a "-" at every 9 indices because the players now have a rank. This is solved by iterating backwards, and if the element is found in the
    #    team_list variable (a default team in Halo 2), then a '-' is inserted after to make the Team rows 9 elements wide.
    #
    #  Finally, as if that wasn't enough - These are ranked, and there is a flag that verifies the game was a clan match, but instead of saying 'Red Team' and 
    #    'Blue Team', it's the clan named by a 12 year old. These are indiscernible from an Xbox Live gamertag since they have the same requirements.  Because the 
    #    players have a 9 element wide row, clan rows do not, and each field will never have an alphabet character - starting at the 5th row, or index [45], check
    #    8 elements ahead.  If it has an alphabetical character, it must be a clan row since 8 elements ahead of every character will not possess an alphabetical
    #    character.  For easier processing, a '*' is inserted following the clan name as opposed to '-'.
    #
    #  Implementing all of these scenarios will result in a 9 element wide 2D array of the games carnage report for easy processing.
        
    # Handle case where it's a clan match....
    # Clan matches are unique in the sense that instead of 'Red/Blue Team', it's the clan names which are practically indiscernable to an Xbox Live gamertag
    if "Clanmatch" in playlist:
        # Increment total clan games by 1
        global clanmatch_games
        clanmatch_games += 1
        # Increase the <header> row from 8 to 9
        carnage_report.insert(1, 'Rank')
        # Guaranteed (or your money back) to be the index following the first clan name.
        # @NOTE - A '*' is used instead of '-' to quickly test for a Clan vs. player
        carnage_report.insert(10, '*')
        
        # Start at first gamertag in first clan - always #18 after previous inserts
        # @NOTE - can **PROBABLY** beef this up to 45.  45 would represent header(9) + clan1(9) + gamertag(9)*3 = 45.  The second clan wouldn't be shown until then given clan matches were a minimum of 3
        #       --> but what if someone disconnected and Bungie purged that data?
        i = 45
        while i < len(carnage_report):
            # Checks the element 8 ahead for an a-z/A-Z character
            if bool(re.match('^(?=.*[a-zA-Z])', carnage_report[i+8])) and carnage_report[i+8] != 'N/A':
                # if so, we're at the clan name
                #print("Clan name = " + carnage_report[i])
                # insert accordingly
                carnage_report.insert(i + 1, '*')
                break
            # Iterate by 9 to move ahead an entire row to the next gamertag or clan name to test
            i += 9

        # Players determined by dividing by 9.  Then remove the two clan lines and header (-3)
        player_count = int((len(carnage_report) / 9) - 3)
        
        # This is needed due to a few games registered as "Clanmatch" without major/minor - but the size of teams varied
        if player_count <= 8:
            global clanmatch_games_minor
            clanmatch_games_minor += 1
        else:
            global clanmatch_games_major
            clanmatch_games_major +=1 
           
        '''
        # Match was uneven
        if player_count % 2 == 1:  
            if debug is True:
                print("Uneven clan match.")
                if player_count < 8:
                    print("Hold the phone, we have an uneven Minor Clanmatch")
            
        '''
        
    # If not ranked, each gamertag should be appended with a '-' as a hack
    elif is_ranked is False:
        i = 1
        while i < len(carnage_report):
            carnage_report.insert(i, '-')
            i += 9
        # Always enter the Rank at this position - overwrites the '-'
        carnage_report[1] = 'Rank'
    else:
        carnage_report.insert(1, 'Rank')
        for i in reversed(carnage_report):
            # If entry is a Default Team, insert a '-'
            if i in team_list:
                carnage_report.insert(carnage_report.index(i) + 1, '-')
    
    #print(carnage_report)
    carnage_report = np.array(carnage_report).reshape(int(len(carnage_report)/9),9) 
    
    return carnage_report         
        
# Create a list of all the files in the data directory with game data        
raw_data_files = []

# If manually set to false, a new master file will be written first
if update_master_list is True:  
    # Populate with all files since we are aggregating a master list
    raw_data_files = glob.glob(root_directory + "*_raw_data.txt")
    # Iterate through each file in directory ending in _raw_data.txt
    for f in raw_data_files:
        with open(f, "r") as infile:
            content = infile.readlines()
        content = [x.strip() for x in content]
        # Prints lenght of individual file
        if debug is True:
            print("Adding '" + f + "' with length " + len(content) + " to global_stats")
        # Extends the global_stats list with all content in file
        global_stats.extend(content)
    

    # Remove duplicates
    global_stats = list(set(global_stats))
    # Sort the stats by game_id so earlier games are at top of file
    global_stats.sort(key=lambda x: int(x.split('|', maxsplit=1)[0][1:-1]))
    
    # Open file to create / write / overwrite
    with open(root_directory + "__master_sorted_data.txt", "w") as output_file:
        for i in global_stats:
            output_file.write((i + '\n'))
            
# If master list was not updated, populate global_stats with the current __master_sorted_data.txt or gamertag
else:
    # @TODO - Will Crash if not updating master list - but pulling from it
    if not gamertag:
        raw_data_files.append(root_directory + "__master_sorted_data.txt")
    else:
        for gt in gamertag:
            raw_data_files.append(root_directory + gt + "_raw_data.txt")
            
    # See which files are being considered
    if debug is True:
        print("\n")
        print("Pulling the following requests for " + str(gamertag) + " from these text files:")
        print("----------------------------------------------------------------")
        for i in raw_data_files:
            print(i)
            
    for f in raw_data_files:
        try:
            with open(f) as infile:
                local_stats = infile.readlines()
            # Strips all new line characters
            local_stats = [x.strip() for x in local_stats]
            global_stats.extend(local_stats)
        except:
            print("No file found for \\data\\" + gt + "_raw_data.txt.  Ignoring..")
            
        
    # Remove duplicates    
    global_stats = list(set(global_stats))

if not global_stats:
    print("Stats list empty - exiting...")
    input()
    exit(0)

# Populate the players[] list by truncating the gamertags from the file names
# @TODO - will crash on masterlist...
for i in raw_data_files:
    players.append(i.split("__data\\")[1].split("_raw_data.txt")[0])

# See which players were found as sources
if debug is True:
    print("\n")
    print("The following players had raw data files:")
    print("---------------------------------")
    for i in players:
        print(i) 


    
# global_stats is now a list of every line from each file in gamertag[]
total_games = str(len(global_stats))

print("\n")
print("Games found: " + total_games)

''' BIG PARSER HERE '''
# each line in global stats has the following layout:
# [game_id]|['game_type' on 'map', 'playlist', 'date, time', 'un/ranked']|[carnage_report]
# @TODO - reversed() might not be needed here... check removing duplicates above
for i in reversed(global_stats):

    # Splits into [0] = game_id, [1] = summary, and [2] = carnage report
    structure = i.split('|')
    
    # Removes the single quotes before and after the game_id and casts as an integer
    game_id = int(structure[0][1:-1])
    
    # Takes the first element of [1], which is the summary, strips the brackets, and splits from the right at " on ".
    # The maxsplit flag is set to 1 to handle the rare game type "2 on 1 on <map>". 
    game_type = structure[1].strip('][').split(', ')[0].rsplit(" on ", maxsplit=1)[0][1:]
    
    # Takes the first element of [1], which is the summary, strips the brackets and takes the last item from the split at " on ".
    map_played = structure[1].strip('][').split(', ')[0].split(" on ")[-1][:-1]
    
    # Takes the first element of [1], which is the summary, stripes
    # @TODO - Make less dangerous - what if empty??
    playlist = structure[1].strip('][').split(', ')[1][12:-1]
    
    # Splits the elements of [1] by ", " after stripping the brackets, takes the 3rd element, and truncates the initial "'"
    date = structure[1].strip('][').split(', ')[2][1:]
    
    # Input the 3 parts of date[] above as integers, and use strftime() to output the day
    # Shamlessly stolen from: https://stackoverflow.com/questions/9847213/how-do-i-get-the-day-of-week-given-a-date/51516223#51516223  
    day = datetime.date(int(date.split('/')[2]), int(date.split('/')[0]), int(date.split('/')[1])).strftime('%A')
    
    # Splits the elements of [1] by ", " after stripping the brackets, takes the 4th element, and truncates the final "'"
    time = adjust_time(structure[1].strip('][').split(', ')[3][:-1])

    # Populate the dictionaries for the games being parsed
    dictionary_insert(map_played, map_dictionary)
    dictionary_insert(date,       date_dictionary)
    dictionary_insert(time,       time_dictionary)
    dictionary_insert(game_type,  game_type_dictionary)
    dictionary_insert(day,        weekday_dictionary)
    dictionary_insert(playlist,   playlist_dictionary)
    
    # Quick read to see if game was marked as Ranked. This assumes Halo2_StatGenerator was correct in its handling of the ExpBar flag
    is_ranked = True if structure[1].strip('][').split(', ')[4][1:-1] == 'Ranked' else False    
    # Clan matches are unique in the sense that instead of 'Red/Blue Team', it's the clan names which are practically indiscernable to an Xbox Live gamertag
    is_clanmatch = True if "Clanmatch" in playlist else False
    # @TODO - Some gamertags still have weird custom games names intact, but it's too few to care. See complete Playlist breakdown for stragglers
    is_custom = True  if playlist == "Arranged Game" else False
    
    # Simple counters
    if is_ranked is True:
        ranked_games += 1 
    else:
        unranked_games += 1 
        
    if is_custom:
        custom_games += 1
        
    # Convert the data string into an actual list
    carnage_report_data = ast.literal_eval(structure[2])

    # Passes in the carnage report as a list, and uses playlist / is_ranked to return a 9 element wide table
    carnage_report = process_carnage_report(carnage_report_data, playlist, is_ranked)

    # These buffers reset for each game. Going down the rows, each is updated accordingly so when the gamertag matches, it can apply the correct team.
    clan_name_buffer = ""
    team_color_buffer = ""
    
    # Assumes true, but if a second default team is hit before the gamertag, then it's a loss.  Meant for ranked only.
    winning_team = True
    
    # Reset to 0,0.  At each team color, flip a value so if the second is false when the gamertag is hit, it's a win.  If it's true, it's a loss. If both are false, it's a FFA
    winning_tracker = [False, False]
    
    # If any Head to Head gamertags is any element of the carnage report - assume it counts
    head_to_head_enabled = True if any(q in vs_gamertag for q in carnage_report_data) else False
    
    
    
    # Iterate through carnage report, ignoring the header row
    for i in carnage_report[1:]:
    
        # If the player name is any of the submitted gamertags, enable
        is_gamertag = True if i[0] in gamertag else False
        
        if is_gamertag and is_clanmatch:
            # Append the latest Clan name and increase by 1
            dictionary_insert(clan_name_buffer, clans_dictionary)
    
        # First and foremost, if a player - add them to the player dictionary
        if i[0] not in team_list and i[1] != '*' and i[0] not in gamertag:
            dictionary_insert(i[0], player_dictionary)
        
        # Head to Head .....
        # If ranked and vs. player is in game, add it.
        if head_to_head_enabled and is_ranked:
            if i[0] in vs_gamertag:
                kda = list(map(int, i[2:5]))
                head_to_head_opponent += kda
                head_to_head_games += 1
            if i[0] in gamertag:
                kda = list(map(int, i[2:5]))
                head_to_head_player += kda
                
         
        # Determines if a clan row
        if i[1] == '*':
            # Update latest clan name as it goes down the list
            clan_name_buffer = i[0]
            
        # @NOTE - CANNOT use if gamertag in - because XBL Guests had gamertag(G)
        # Update all the K/D/A global variables
        if is_gamertag:
            # Convert to a 3 element int array for [Kills, Assists, Deaths]
            # @NOTE - 'kad' seems weird, but 'kda' seems to read better although it's not lined up
            kda = list(map(int, i[2:5]))
            
            # Suicides, Betrayals seem to have been purged... All 0's
            # @TODO Score - Flag? Bomb? TS? Oddball? KOTH?
            # sb = list(map(int, i[6:8]))
            player_stats_global += kda
           
            # Map K/D/A processing
            if map_played in map_kd_dictionary:
                map_kd_dictionary[map_played][0:3] += kda
            # For the first time a map is played - initialize a 3 element array
            else:
                map_kd_dictionary[map_played] = np.zeros((4,), dtype=float)
                map_kd_dictionary[map_played][0:3] += kda
            
            if not is_custom:
                # If it's not custom, it must but matchmade..
                player_stats_matchmaking += kda 
                
            if is_ranked:
            
                # Retrieve highest level by comparing if the second element is a number (rank)
                if int(i[1]) > int(max_rank_overall[0]):
                    max_rank_overall[0] = i[1]  
                    max_rank_overall[1] = game_id
                if not is_clanmatch and int(i[1]) > int(max_rank_no_clan[0]):
                    max_rank_no_clan[0] = i[1]        
                    max_rank_no_clan[1] = game_id
                
                # Quirky stat tracking - don't ask #
                # Add K/D/A to ranked stats
                player_stats_ranked += kda
                
                # If no team color has populated the buffer, it must be a ranked FFA
                if team_color_buffer == "":
                    player_stats_ranked_ffa += kda
                    ranked_ffa_games += 1
                # Otherwise, must be a ranked Team Game:
                else:
                    player_stats_ranked_team += kda
                    ranked_team_games += 1
                    dictionary_insert(team_color_buffer, team_color_ranked_dictionary)
                
                # Self documenting...?
                if is_clanmatch:
                    player_stats_clan += kda
                else:
                    player_stats_ranked_no_clan += kda
                    
                
                # Montly KDA
                monthly_kda_dictionary[calendar.month_name[int(date.split('/')[0])]][0:3] += kda
                # Increment total games by one
                monthly_kda_dictionary[calendar.month_name[int(date.split('/')[0])]][3] += 1
                
                # Win Rate processing...
                if not winning_tracker[0]:
                    # Skip ranked FFA for now...
                    continue
                # Check second flag for win / loss
                if not winning_tracker[1]:
                    ranked_win_rate[0] += 1
                else:
                    ranked_win_rate[1] += 1
       
            # If not ranked, it's either a custom game or unranked matchmaking game
            if is_custom:
            
                player_stats_customs += kda
                custom_games += 1
                # Without a team color assigned, must be FFA
                if not team_color_buffer:
                    custom_ffa_games += 1
                else:
                    custom_team_games += 1
                    dictionary_insert(team_color_buffer, team_color_customs_dictionary)


                
        # Process team colors in team customs
        if i[0] in team_list:
            # Update Team color as rows get parsed
            team_color_buffer = i[0]
            # Win Rate - 
            # @NOTE - programming is getting sloppy...too many late nights.  
            if not winning_tracker[0]:
                winning_tracker[0] = True
            else :
                winning_tracker[1] = True
           

    
# Sort the player dictionary by most played with --> least
sorted_player_list = sorted(player_dictionary.items(), key = lambda x:x[1], reverse=True)
# Sort the map dictionary by most played --> least
sorted_map_played_list = sorted(map_dictionary.items(), key=itemgetter(1), reverse=True)
# Sort the game_type dictionary by most played --> least
game_type_list_sorted  = sorted(game_type_dictionary.items(), key=itemgetter(1), reverse=True)
# Sort the playlist dictionary by most played --> least
playlist_list_sorted   = sorted(playlist_dictionary.items(), key=itemgetter(1),reverse=True)
# Sort the Clans played in by most played with --> least
clans_list_sorted      = sorted(clans_dictionary.items(), key=itemgetter(1), reverse=True)
# Sort the Team Color chosen in team custom games by most selected --> least
team_color_customs_list_sorted = sorted(team_color_customs_dictionary.items(), key=itemgetter(1), reverse=True)
# Sort the Team Color chosen in team ranked games by most selected --> least
team_color_ranked_list_sorted = sorted(team_color_ranked_dictionary.items(), key=itemgetter(1), reverse=True)
# Sort the games played per day dictionary
games_played_per_day_list_sorted = sorted(date_dictionary.items(), key=itemgetter(1), reverse=True)


''' Beginning of the Outputs '''

# Outputs the sorted list of Maps by most played
s = "\nMap Selection Frequency\n------------------------------"
output_stat(s) 
    
for i in sorted_map_played_list:
    # Create a nicely formatted string showing "map : count / total_games"
    s = i[0].ljust(15) + ": " + str(i[1]).rjust(5) + " / " + total_games
    output_stat(s) 
        

# Outputs the sorted list of Game Types by most played
s = "\nGame Type Frequency\n-----------------------------------"
output_stat(s) 
 
for i in game_type_list_sorted:
    # Create a nicely formatted string showing "game_type : count / total_games"
    s = i[0].ljust(20) + ": " + str(i[1]).rjust(5) + " / " + total_games
    output_stat(s) 
    
# Outputs the sorted list of Playlist by most played
s = "\nPlaylist Frequency\n-----------------------------------"
output_stat(s)  
    
for i in playlist_list_sorted:
    # Create a nicely formatted string showing "game_type : count / total_games"
    s = i[0].ljust(20) + ": " + str(i[1]).rjust(5) + " / " + total_games
    output_stat(s) 

# Outputs the sorted list of Clans by most played with
s = "\nClanmatch Frequency\n--------------------------------------------"
output_stat(s) 
    
for i in clans_list_sorted:
    # Create a nicely formatted string showing "game_type : count / total_games"
    s = i[0].ljust(20) + ": " + str(i[1]).rjust(5) + " / " + str(clanmatch_games) + " | " + "{:.2%}".format(int(i[1])/int(clanmatch_games)).rjust(7)
    output_stat(s)  
        
# Outputs the sorted list of Team Color by most played as in Customs
s = ""
s += "\nTeam Color [Customs] Selection Frequency\n----------------------------------------\n"   
for i in team_color_customs_list_sorted:
    # Create a nicely formatted string showing "game_type : count / total_games"
    s += i[0].ljust(20) + ": " + str(i[1]).rjust(5) + " / " + str(custom_team_games) + " custom team games | " + "{:.2%}".format(i[1]/custom_team_games).rjust(7) + "\n"
output_stat(s)           
   
# Outputs the sorted list of Team Color by most played as in Ranked
s = "\nTeam Color [Ranked] Selection Frequency\n---------------------------------------\n"
for i in team_color_ranked_list_sorted:
    if i[1]:
        # Create a nicely formatted string showing "game_type : count / total_games"
        s += i[0].ljust(20) + ": " + str(i[1]).rjust(5) + " / " + str(ranked_team_games) + " ranked team games | " + "{:.2%}".format(i[1]/ranked_team_games).rjust(7) + "\n"
output_stat(s) 
        
        
# Parses the date dictionary for highest value and outputs the day and count for most games played 
s = ""
s += "\n"
s += "Top 15 days with most games played:\n-----------------------------------\n"
for i in range(0, 15):
    s += "  " + games_played_per_day_list_sorted[i][0].rjust(10) + ": " + str(games_played_per_day_list_sorted[i][1]).rjust(4) + "\n"
output_stat(s)

# Parses the time dictionary for highest value and outputs the time and count for most games played
s = ""
s += "\n"
s += "Most games played at this hour:\n-------------------------------\n"
most_hour_played = key_with_max_value(time_dictionary)
s += most_hour_played + " : " + str(time_dictionary[most_hour_played]) + " games played at this hour"
output_stat(s)

# Outputs a complete hour by hour breakdown of games played
s = ""
s += "\n"
s += "Complete hour by hour breakdown:\n--------------------------------\n"
s += dict_to_string(time_dictionary)
output_stat(s)

# Outputs a complete day by day breakdown of games played
s = ""
s += '\n'
s += "Complete day by day breakdown:\n------------------------------\n"
s += dict_to_string(weekday_dictionary)
output_stat(s)

'''
# @TODO - Remove? Already in list above...
# Parses the playlist dictionary for highest value and outputs the playlist and count for most games played
s = ""
s += "\n"
s += "Most frequently played playlist:\n--------------------------------\n"
most_played_playlist = key_with_max_value(playlist_dictionary)
s += most_played_playlist + " : " + str(playlist_dictionary[most_played_playlist]) + " games played in this playlist."
output_stat(s)
'''

# Build stat table for Ranked vs. Unranked.  Uses hardcoded justify and % format 
s = ""
s += "\nRanked vs. Unranked:\n------------------------------------------"
s += "\nRanked Games: ".ljust(18) + str(ranked_games).rjust(6) + " / " + str(total_games).rjust(5) + " | " + "{:.2%}".format(int(ranked_games)/int(total_games)).rjust(7)
s += "\n                   ----------------------"
s += "\nUnranked Games: ".ljust(18) + str(unranked_games).rjust(6) + " / " + str(total_games).rjust(5) + " | " + "{:.2%}".format(unranked_games/int(total_games)).rjust(7)
s += "\n                   ----------------------"
s += "\nCustom Games: ".ljust(18) + str(custom_games).rjust(6) + " / " + str(total_games).rjust(5) + " | " + "{:.2%}".format(custom_games/int(total_games)).rjust(7)
s += "\n                   ----------------------"
if custom_games:
    s += "\n  [Team]: ".ljust(18) + str(custom_team_games).rjust(6) + " / " + str(custom_games).rjust(5) + " | " + "{:.2%}".format(custom_team_games/int(custom_games)).rjust(7)
    s += "\n  [FFA ]: ".ljust(18) + str(custom_ffa_games).rjust(6) + " / " + str(custom_games).rjust(5) + " | " + "{:.2%}".format(custom_ffa_games/int(custom_games)).rjust(7)
s += "\n------------------------------------------"
s += "\nClan Matches: ".ljust(18) + str(clanmatch_games).rjust(6) + " / " + str(total_games).rjust(5) + " | " + "{:.2%}".format(clanmatch_games/int(total_games)).rjust(7)
s += "\n                   ----------------------"
if clanmatch_games:
    s += "\n  [Minor]: ".ljust(18) + str(clanmatch_games_minor).rjust(6) + " / " + str(clanmatch_games).rjust(5) + " | " + "{:.2%}".format(clanmatch_games_minor/int(clanmatch_games)).rjust(7)
    s += "\n  [Major]: ".ljust(18) + str(clanmatch_games_major).rjust(6) + " / " + str(clanmatch_games).rjust(5) + " | " + "{:.2%}".format(clanmatch_games_major/int(clanmatch_games)).rjust(7)
output_stat(s)

s = ""
s += "\n"
s += "\n           Maximum Rank Achieved overall: " + str(max_rank_overall[0]).rjust(3) + " in game ID " + str(max_rank_overall[1])
s += "\nMaximum Rank Excl. Clan Achieved overall: " + str(max_rank_no_clan[0]).rjust(3) + " in game ID " + str(max_rank_no_clan[1])
output_stat(s)


# Outputs a complete hour by hour breakdown of games played
s = ""
s += "\n"
s += "Complete Monthly Ranked K/D breakdown:\n--------------------------------\n"
for month, kda in monthly_kda_dictionary.items():
    s += month.ljust(10) + ": " + "{:.3f}".format(kda[0]/kda[2]).rjust(5) + " over " + str(int(kda[3])).rjust(4) + " games\n"
output_stat(s)


# Output total K/D/A's & ratios 
s = ""
s += "\n"
s += "\nKills / Assists / Deaths Overview:                                                                     K/D "
s += "\n-----------------------------------------------------------------------------------------------------------"
s += "\nGlobal Kills / Assists / Deaths:".ljust(55) 
s += str(player_stats_global[0]).rjust(6) + " Kills | " + str(player_stats_global[1]).rjust(6) + " Assists | " + str(player_stats_global[2]).rjust(6) + " Deaths | " + "{:.3f}".format(player_stats_global[0]/player_stats_global[2]).rjust(5)
s += "\nRanked Kills / Assists / Deaths:".ljust(55) 
s += str(player_stats_ranked[0]).rjust(6) + " Kills | " + str(player_stats_ranked[1]).rjust(6) + " Assists | " + str(player_stats_ranked[2]).rjust(6) + " Deaths | " + "{:.3f}".format(player_stats_ranked[0]/player_stats_ranked[2]).rjust(5)
s += "\nRanked Team Kills / Assists / Deaths:".ljust(55) 
s += str(player_stats_ranked_team[0]).rjust(6) + " Kills | " + str(player_stats_ranked_team[1]).rjust(6) + " Assists | " + str(player_stats_ranked_team[2]).rjust(6) + " Deaths | " + "{:.3f}".format(player_stats_ranked_team[0]/player_stats_ranked_team[2]).rjust(5)
s += "\nRanked FFA Kills / Assists / Deaths:".ljust(55) 
s += str(player_stats_ranked_ffa[0]).rjust(6) + " Kills | " + str(player_stats_ranked_ffa[1]).rjust(6) + " Assists | " + str(player_stats_ranked_ffa[2]).rjust(6) + " Deaths | " + "{:.3f}".format(player_stats_ranked_ffa[0]/player_stats_ranked_ffa[2]).rjust(5)
s += "\nRanked Excl. Clanmatches Kills / Assists / Deaths:".ljust(55) 
s += str(player_stats_ranked_no_clan[0]).rjust(6) + " Kills | " + str(player_stats_ranked_no_clan[1]).rjust(6) + " Assists | " + str(player_stats_ranked_no_clan[2]).rjust(6) + " Deaths | " + "{:.3f}".format(player_stats_ranked_no_clan[0]/player_stats_ranked_no_clan[2]).rjust(5)
s += "\nClanmatch Kills / Assists / Deaths:".ljust(55) 
s += str(player_stats_clan[0]).rjust(6) + " Kills | " + str(player_stats_clan[1]).rjust(6) + " Assists | " + str(player_stats_clan[2]).rjust(6) + " Deaths | " + "{:.3f}".format(player_stats_clan[0]/player_stats_clan[2]).rjust(5)
s += "\nCustoms Kills / Assists / Deaths:".ljust(55) 
s += str(player_stats_customs[0]).rjust(6) + " Kills | " + str(player_stats_customs[1]).rjust(6) + " Assists | " + str(player_stats_customs[2]).rjust(6) + " Deaths | " + "{:.3f}".format(player_stats_customs[0]/player_stats_customs[2]).rjust(5)
s += "\nMatchmaking Kills / Assists / Deaths:".ljust(55) 
s += str(player_stats_matchmaking[0]).rjust(6) + " Kills | " + str(player_stats_matchmaking[1]).rjust(6) + " Assists | " + str(player_stats_matchmaking[2]).rjust(6) + " Deaths | " + "{:.3f}".format(player_stats_matchmaking[0]/player_stats_matchmaking[2]).rjust(5)
output_stat(s)

# Map specific K/D
s = ""
s += "\n"
s += "\nMap Specific K/D: "
s += "\n----------------------\n"
# Alphabetically sort the maps
map_kd_dictionary = dict( sorted(map_kd_dictionary.items(), key=lambda x: x[0].lower()) )
# Calculate the k/d from the first 3 elements and store in 4th
for m, kda in map_kd_dictionary.items():
    kda[3] = kda[0]/kda[2]
    s += m .ljust(15) + ": " + "{:.3f}".format(kda[3]) + "\n"
output_stat(s)

# Most Players played w/ preview
s = ""
s += "\n"
s += "\nTop 20 Most Played with:\n------------------------\n"
for i in range(0, 20):
    s += "  " + sorted_player_list[i][0].ljust(16) + ": " + str(sorted_player_list[i][1]).rjust(5) + "\n"
output_stat(s)

# Win Rate Outputs
s = ""
s += "\n"
s += "\nRanked Team Excl. Clan Win Rate\n--------------------------------"
wins = int(ranked_win_rate[0])
losses = int(ranked_win_rate[1])
rate = float(wins/(ranked_team_games))
s += "\nWins: " + str(wins).rjust(5) + " | Losses : " + str(losses).rjust(5) + " | Win Rate: " + "{:.2%}".format(rate).rjust(5) 
output_stat(s)


# Head to Head Mode:
if vs_gamertag:
    s = ""
    s += "\n"
    s += "\nHead to Head - Ranked Games Only"
    s += "\n--------------------------------"
    s += "\nGamertag(s): " + str(gamertag).ljust(80, '-') + " | " + "{:.3f}".format(head_to_head_player[0]/head_to_head_player[2]).rjust(5)
    s += "\n  vs."
    s += "\nGamertag(s): " + str(vs_gamertag).ljust(80, '-') + " | " + "{:.3f}".format(head_to_head_opponent[0]/head_to_head_opponent[2]).rjust(5)
    s += "\n"
    s += "\nData taken from " + str(head_to_head_games) + " games."
    
    if debug is True:
        ## DEBUG ##
        s += "\n\n## DEBUG ##"
        s += "\n" + str(head_to_head_player[0]) + "|" + str(head_to_head_player[2]) + "|||" + str(head_to_head_opponent[0]) + "|" + str(head_to_head_opponent[2])
        
    output_stat(s)


# Close output file if writing
if write_to_file_enabled is True:
    output_file.close()

''' Testing Zone '''
# Prints out games at certain hours
'''

# Converting string to list 
new_list = string_list.strip('][').split(', ') 

if int(time.split(':')[0]) == 4 and time.split()[1] == "AM":
    print(i[1:10])
'''
# END TEST #
    
''' End Testing '''

''' Deprecated Zone '''

'''
# Old method of parsing time. Far inferior.

# If time is PM, add 12 hours for a 24 hour time frame
if time.split()[1] == "PM":
    time = str(int(time.split(':')[0]) + 12)
# If it's AM and less than 10, append a "0" to the front as a shitty hack to sorting the time in order
# @TODO - On second thought, this sucks.  Pre populate the dictionary with 1 -> 24, so no need to sort, and counts for people who have 0 in that hour
# @TODO - Because my friend Husker doesn't commit war crimes - make the dictionary entry " 1 AM" --> "11 PM"
else:
    if int(time.split(':')[0]) < 10:
        time = "0" + time
'''