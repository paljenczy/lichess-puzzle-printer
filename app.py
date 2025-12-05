#!/usr/bin/env python3
"""
Web UI for Lichess Puzzle Generator
Flask web application to generate printable chess puzzles
"""

import os
import tempfile
from flask import Flask, render_template, request, jsonify, send_file
from puzzle_printer import PuzzleFetcher, PuzzlePDFGenerator

app = Flask(__name__)

# Theme descriptions for display
THEME_DESCRIPTIONS = {
    'advancedPawn': 'Advanced Pawn - Pawn close to promotion',
    'advantage': 'Advantage - Win material or checkmate',
    'anastasiaMate': 'Anastasia\'s Mate - Knight and rook mate',
    'arabianMate': 'Arabian Mate - Knight and rook mate pattern',
    'attackingF2F7': 'Attacking f2/f7 - Attack weak f-pawn',
    'attraction': 'Attraction - Lure piece to bad square',
    'backRankMate': 'Back Rank Mate - Checkmate on back rank',
    'bishopEndgame': 'Bishop Endgame - Bishop vs bishop/pawns',
    'bodenMate': 'Boden\'s Mate - Two bishops checkmate',
    'capturingDefender': 'Capturing Defender - Remove defending piece',
    'castling': 'Castling - Castle to safety or attack',
    'clearance': 'Clearance - Clear square for another piece',
    'crushing': 'Crushing - Winning by force',
    'defensiveMove': 'Defensive Move - Find defensive resource',
    'deflection': 'Deflection - Divert defending piece',
    'discoveredAttack': 'Discovered Attack - Reveal attack by moving',
    'doubleBishopMate': 'Double Bishop Mate - Two bishops mate',
    'doubleCheck': 'Double Check - Check with two pieces',
    'dovetailMate': 'Dovetail Mate - Queen checkmate pattern',
    'enPassant': 'En Passant - Special pawn capture',
    'endgame': 'Endgame - Few pieces remaining',
    'equality': 'Equality - Achieve equal position',
    'exposedKing': 'Exposed King - Attack exposed king',
    'fork': 'Fork - Attack two pieces at once',
    'hangingPiece': 'Hanging Piece - Win undefended piece',
    'hookMate': 'Hook Mate - Rook and knight/pawn mate',
    'interference': 'Interference - Block piece\'s defense',
    'intermezzo': 'Intermezzo - In-between move',
    'kingsideAttack': 'Kingside Attack - Attack on kingside',
    'knightEndgame': 'Knight Endgame - Knight and pawns',
    'long': 'Long Puzzle - Many moves required',
    'master': 'Master Game - From master-level play',
    'masterVsMaster': 'Master vs Master - Both players masters',
    'mate': 'Checkmate - Deliver checkmate',
    'mateIn1': 'Mate in 1 - Checkmate in one move',
    'mateIn2': 'Mate in 2 - Checkmate in two moves',
    'mateIn3': 'Mate in 3 - Checkmate in three moves',
    'mateIn4': 'Mate in 4 - Checkmate in four moves',
    'mateIn5': 'Mate in 5 - Checkmate in five moves',
    'middlegame': 'Middlegame - Middle phase of game',
    'oneMove': 'One Move - Single-move solution',
    'opening': 'Opening - Early game position',
    'pawnEndgame': 'Pawn Endgame - Only pawns and kings',
    'pin': 'Pin - Pin opponent\'s piece',
    'promotion': 'Promotion - Promote pawn to queen/piece',
    'queenEndgame': 'Queen Endgame - Queen and pawns',
    'queenRookEndgame': 'Queen & Rook Endgame - Queen and rook',
    'queensideAttack': 'Queenside Attack - Attack on queenside',
    'quietMove': 'Quiet Move - Non-forcing winning move',
    'rookEndgame': 'Rook Endgame - Rook and pawns',
    'sacrifice': 'Sacrifice - Give up material for advantage',
    'short': 'Short Puzzle - Few moves required',
    'skewer': 'Skewer - Attack through another piece',
    'smotheredMate': 'Smothered Mate - Knight checkmate',
    'superGM': 'Super GM - From top grandmaster games',
    'trappedPiece': 'Trapped Piece - Win trapped piece',
    'underPromotion': 'Under Promotion - Promote to non-queen',
    'veryLong': 'Very Long Puzzle - Many moves required',
    'xRayAttack': 'X-Ray Attack - Attack through pieces',
    'zugzwang': 'Zugzwang - Any move worsens position',
}

# Global singleton puzzle fetcher to avoid reloading database on every request
_puzzle_fetcher = None

def get_puzzle_fetcher():
    """Get or create the global puzzle fetcher instance."""
    global _puzzle_fetcher
    if _puzzle_fetcher is None:
        _puzzle_fetcher = PuzzleFetcher()
    return _puzzle_fetcher

def get_theme_description(theme: str) -> str:
    """Get human-readable description for a theme."""
    return THEME_DESCRIPTIONS.get(theme, theme)


@app.route('/')
def index():
    """Render the main page."""
    # Get available themes from database
    fetcher = get_puzzle_fetcher()
    themes = fetcher.get_available_themes()
    
    # Create list of themes with descriptions
    themes_with_desc = [(t, get_theme_description(t)) for t in themes]
    
    return render_template('index.html', themes=themes_with_desc)


@app.route('/generate', methods=['POST'])
def generate_puzzles():
    """Generate puzzle PDF based on user settings."""
    tmp_filename = None
    try:
        data = request.json
        
        # Validate input
        theme = data.get('theme', 'mateIn2')
        min_rating = int(data.get('minRating', 800))
        max_rating = int(data.get('maxRating', 1400))
        count = int(data.get('count', 36))
        
        # Validate ranges
        if min_rating >= max_rating:
            return jsonify({'error': 'Minimum rating must be less than maximum rating'}), 400
        
        if count < 1 or count > 36:
            return jsonify({'error': 'Puzzle count must be between 1 and 36'}), 400
        
        # Fetch puzzles using singleton fetcher
        fetcher = get_puzzle_fetcher()
        puzzles = fetcher.fetch_puzzles_by_theme(theme, min_rating, max_rating, count)
        
        if not puzzles:
            return jsonify({'error': 'No puzzles found matching your criteria'}), 404
        
        # Generate PDF in a temporary file
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.pdf', delete=False) as tmp_file:
            tmp_filename = tmp_file.name
        
        # Get theme description for PDF title
        theme_desc = get_theme_description(theme)
        
        generator = PuzzlePDFGenerator(tmp_filename)
        generator.generate(puzzles, theme_desc)
        
        # Send the file and schedule cleanup
        response = send_file(
            tmp_filename,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'chess_puzzles_{theme}.pdf'
        )
        
        # Schedule file deletion after a short delay (handled by the OS)
        # The file will be automatically cleaned up
        return response
    
    except Exception as e:
        app.logger.error(f"Error generating puzzles: {e}")
        # Clean up temp file if it was created
        if tmp_filename and os.path.exists(tmp_filename):
            try:
                os.unlink(tmp_filename)
            except:
                pass
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 Chess Puzzle Generator - Web UI")
    print("="*60)
    print("\n📱 Open your browser and go to:")
    print("\n    http://localhost:5000\n")
    print("="*60 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
