from flask import Flask, jsonify, request
from flask_cors import CORS
import pandas as pd
import numpy as np
import os

from flask_cors import CORS

app = Flask(__name__)
CORS(app)


# Determine the correct path to the CSV file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
file_name = 'nba_player_stats_2020_2025.csv'
file_path = os.path.join(BASE_DIR, file_name)

# Alternative absolute path if needed
alt_path = r'C:\Users\adhit\OneDrive\bettingsAlgorithm\nba-bettingRiskMinimizer\nba_vegasKiller\nba_player_stats_2020_2025.csv'

# Check if the file exists and load the correct path
if os.path.exists(file_path):
    df = pd.read_csv(file_path)
    print("File loaded from base directory.")
elif os.path.exists(alt_path):
    df = pd.read_csv(alt_path)
    print("File loaded from alternate path.")
else:
    raise FileNotFoundError("CSV file not found in both base and alternate paths.")

# Load schedule data for current or selected date
game_schedule = pd.read_csv(os.path.join(BASE_DIR, 'nba_game_schedule.csv'))

def get_active_players(date):
    # Ensure date format consistency
    game_schedule['DATE'] = pd.to_datetime(game_schedule['DATE']).dt.strftime('%Y-%m-%d')
    selected_date = pd.to_datetime(date).strftime('%Y-%m-%d')

    if selected_date not in game_schedule['DATE'].values:
        return pd.DataFrame()
    
    active_teams = game_schedule[game_schedule['DATE'] == selected_date]['TEAMS'].values[0].split(',')
    active_teams = [team.strip() for team in active_teams]
    return df[df['TEAM_ABBREVIATION'].isin(active_teams)]

# Helper function to check player availability
def is_player_available(player):
    return player['INJURY_STATUS'].lower() not in ['injured', 'probable', 'out']

# Betting lines dictionary
BETTING_LINES = {
    'Points': 'POINTS_PER_GAME_10G_MODE',
    'Assists': 'ASSISTS_PER_GAME_10G_MODE',
    'Rebounds': 'REBOUNDS_PER_GAME_10G_MODE',
    'P+R+A': 'PRA_10G_MODE'
}

# Calculate best bet recommendations for a player
def calculate_best_bet(player):
    bets = []
    for bet_type, stat_column in BETTING_LINES.items():
        player_stat = player[stat_column]
        line = round(max(0.8 * player_stat, 0.9 * player_stat) * 2) / 2  # Ensuring increments of 0.5
        odds = np.random.choice([-110, -120, -130, +100, +120])
        formatted_odds = f"{odds:+d}" if odds > 0 else str(odds)
        bet_advice = "Over" if player_stat > line else "Under"
        bet_info = {
            "type": bet_type,
            "line": line,
            "odds": formatted_odds,
            "confidence": f"{min(100, round((player_stat / line) * 100, 1))}%",
            "advice": bet_advice
        }
        bets.append(bet_info)
    return bets

# API endpoint to fetch bets
@app.route('/bets', methods=['GET'])
def get_bets():
    date = request.args.get('date')
    if not date:
        return jsonify({"error": "Date parameter is required"}), 400
    
    active_players = get_active_players(date)
    if active_players.empty:
        return jsonify({"message": "No active players found for the selected date."})
    
    available_players = active_players[active_players.apply(is_player_available, axis=1)]
    top_bets = []
    for _, player in available_players.iterrows():
        bets = calculate_best_bet(player)
        best_bet = max(bets, key=lambda x: x['confidence'])
        top_bets.append({
            "player": player['DISPLAY_FIRST_LAST'],
            "team": player['TEAM_ABBREVIATION'],
            "bet_type": best_bet['type'],
            "line": best_bet['line'],
            "odds": best_bet['odds'],
            "confidence": best_bet['confidence'],
            "advice": best_bet['advice']
        })
    
    top_bets_sorted = sorted(top_bets, key=lambda x: (x['confidence'], -int(x['odds'].replace('+', ''))), reverse=True)
    return jsonify(top_bets_sorted[:3])

if __name__ == '__main__':
    app.run(debug=True)
