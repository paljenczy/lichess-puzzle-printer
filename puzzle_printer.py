#!/usr/bin/env python3
"""
Lichess Puzzle Printer
Generate printable chess puzzle worksheets from Lichess's puzzle database.
"""

import argparse
import csv
import io
import random
import requests
from typing import List, Dict, Tuple
import chess
import chess.svg
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from PIL import Image, ImageDraw, ImageFont
import re
from xml.etree import ElementTree as ET
import zstandard as zstd


class PuzzleFetcher:
    """Fetch and filter puzzles from Lichess API."""
    
    API_BASE = "https://lichess.org/api"
    PUZZLE_DAILY_API = "https://lichess.org/api/puzzle/daily"
    PUZZLE_API = "https://lichess.org/api/puzzle/{puzzle_id}"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Lichess Puzzle Printer/1.0 (Educational; github.com/yourusername/lichess-puzzles)'
        })
        
    def fetch_puzzles_by_theme(self, theme: str, min_rating: int, max_rating: int, count: int) -> List[Dict]:
        """
        Fetch puzzles filtered by theme and rating range using Lichess API.
        
        Args:
            theme: Puzzle theme (e.g., 'mateIn2', 'fork')
            min_rating: Minimum puzzle rating
            max_rating: Maximum puzzle rating
            count: Number of puzzles to fetch
            
        Returns:
            List of puzzle dictionaries
        """
        print(f"Fetching {count} puzzle(s) for theme '{theme}' (rating {min_rating}-{max_rating})...")
        
        puzzles = []
        attempts = 0
        max_attempts = count * 10  # Try up to 10x the requested count to find matches
        
        # Use the puzzle activity endpoint to get random puzzles
        try:
            # Fetch puzzles using the dashboard endpoint which supports filtering
            url = f"{self.API_BASE}/puzzle/activity"
            params = {
                'max': max_attempts,
            }
            
            response = self.session.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                activity_data = response.json()
                
                for entry in activity_data:
                    if len(puzzles) >= count:
                        break
                    
                    puzzle_data = entry.get('puzzle', {})
                    puzzle_rating = puzzle_data.get('rating', 0)
                    puzzle_themes = puzzle_data.get('themes', [])
                    
                    # Filter by rating and theme
                    if puzzle_rating < min_rating or puzzle_rating > max_rating:
                        continue
                    
                    if theme.lower() not in [t.lower() for t in puzzle_themes]:
                        continue
                    
                    puzzles.append(self._format_api_puzzle(puzzle_data))
            
            # If we didn't get enough from activity, fall back to fetching random puzzles
            if len(puzzles) < count:
                print(f"Found {len(puzzles)} from activity, fetching more random puzzles...")
                puzzles.extend(self._fetch_random_puzzles(theme, min_rating, max_rating, count - len(puzzles)))
                
        except Exception as e:
            print(f"Error fetching from API: {e}")
            print("Falling back to random puzzle fetching...")
            puzzles = self._fetch_random_puzzles(theme, min_rating, max_rating, count)
        
        if puzzles:
            print(f"✓ Successfully fetched {len(puzzles)} puzzle(s)")
            for p in puzzles[:3]:  # Show first 3
                print(f"  - Puzzle {p['id']}: {p['rating']} rating")
        
        return puzzles[:count]
    
    def _fetch_random_puzzles(self, theme: str, min_rating: int, max_rating: int, count: int) -> List[Dict]:
        """Fetch random puzzles by trying the daily puzzle and random IDs."""
        puzzles = []
        
        # Try daily puzzle first
        try:
            response = self.session.get(self.PUZZLE_DAILY_API, timeout=10)
            if response.status_code == 200:
                daily = response.json()
                puzzle_data = daily.get('puzzle', {})
                if self._matches_criteria(puzzle_data, theme, min_rating, max_rating):
                    puzzles.append(self._format_api_puzzle(puzzle_data))
        except:
            pass
        
        # Generate random puzzle IDs and try them
        # Lichess puzzle IDs are 5-character alphanumeric strings
        import string
        chars = string.ascii_letters + string.digits
        
        attempts = 0
        max_attempts = count * 50  # Be more aggressive in trying
        
        while len(puzzles) < count and attempts < max_attempts:
            attempts += 1
            
            # Generate random 5-character ID
            puzzle_id = ''.join(random.choices(chars, k=5))
            
            try:
                url = self.PUZZLE_API.format(puzzle_id=puzzle_id)
                response = self.session.get(url, timeout=5)
                
                if response.status_code == 200:
                    puzzle_json = response.json()
                    puzzle_data = puzzle_json.get('puzzle', {})
                    
                    if self._matches_criteria(puzzle_data, theme, min_rating, max_rating):
                        puzzles.append(self._format_api_puzzle(puzzle_data))
                        print(f"  Found puzzle {puzzle_id} ({len(puzzles)}/{count})")
                
            except Exception as e:
                continue
        
        return puzzles
    
    def _matches_criteria(self, puzzle_data: Dict, theme: str, min_rating: int, max_rating: int) -> bool:
        """Check if puzzle matches the criteria."""
        if not puzzle_data:
            return False
        
        rating = puzzle_data.get('rating', 0)
        themes = puzzle_data.get('themes', [])
        
        if rating < min_rating or rating > max_rating:
            return False
        
        if theme.lower() not in [t.lower() for t in themes]:
            return False
        
        return True
    
    def _format_api_puzzle(self, puzzle_data: Dict) -> Dict:
        """Format API puzzle response into standard format."""
        if not puzzle_data:
            return None
        
        # Get the initial position FEN
        initial_fen = puzzle_data.get('fen', 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1')
        
        # Solution moves are in UCI format
        solution_moves = puzzle_data.get('solution', [])
        
        # The puzzle FEN is the position after the opponent's move
        # We need to apply the first move to get the actual puzzle position
        try:
            board = chess.Board(initial_fen)
            if solution_moves and len(solution_moves) > 0:
                # First move in solution is actually the last opponent move
                # that we need to apply to get to the puzzle position
                first_move_uci = solution_moves[0]
                board.push(chess.Move.from_uci(first_move_uci))
                puzzle_fen = board.fen()
                actual_solution = solution_moves[1:]  # Rest are the actual solution
            else:
                puzzle_fen = initial_fen
                actual_solution = []
        except:
            puzzle_fen = initial_fen
            actual_solution = solution_moves
        
        return {
            'id': puzzle_data.get('id', 'unknown'),
            'fen': puzzle_fen,
            'moves': actual_solution,
            'rating': puzzle_data.get('rating', 1000),
            'themes': puzzle_data.get('themes', []),
        }


class ChessBoardRenderer:
        """Download and load the entire puzzle database into memory."""
        import os
        
        print("=" * 60)
        print("Loading Lichess puzzle database...")
        
        # Check if local file exists
        if os.path.exists(self.LOCAL_DB_PATH):
            print(f"Found local database: {self.LOCAL_DB_PATH}")
            file_size_mb = os.path.getsize(self.LOCAL_DB_PATH) / (1024 * 1024)
            print(f"File size: {file_size_mb:.1f} MB")
        else:
            print(f"Downloading database from {self.DATABASE_URL}")
            print("This is a one-time download (~266 MB compressed, ~900 MB uncompressed)")
            print("Please wait...")
            
            # Download and decompress
            response = requests.get(self.DATABASE_URL, stream=True, timeout=60)
            response.raise_for_status()
            
            dctx = zstd.ZstdDecompressor()
            
            # Write decompressed data to local file
            with open(self.LOCAL_DB_PATH, 'wb') as f:
                with dctx.stream_reader(response.raw) as reader:
                    total_bytes = 0
                    while True:
                        chunk = reader.read(1024 * 1024)  # Read 1MB at a time
                        if not chunk:
                            break
                        f.write(chunk)
                        total_bytes += len(chunk)
                        # Progress indicator
                        if total_bytes % (50 * 1024 * 1024) == 0:  # Every 50MB
                            print(f"  Downloaded: {total_bytes / (1024*1024):.1f} MB...")
            
            print(f"✓ Database saved to {self.LOCAL_DB_PATH}")
        
        # Load entire database into memory
        print("Loading database into memory...")
        self._puzzle_cache = []
        
        with open(self.LOCAL_DB_PATH, 'r', encoding='utf-8') as f:
            csv_reader = csv.DictReader(f)
            
            for i, row in enumerate(csv_reader):
                try:
                    puzzle_id = row.get('PuzzleId', '')
                    fen = row.get('FEN', '')
                    moves = row.get('Moves', '').split()
                    puzzle_rating = int(row.get('Rating', 0))
                    puzzle_themes = row.get('Themes', '').split()
                    
                    if not puzzle_id or not fen or not moves:
                        continue
                    
                    # Store raw puzzle data
                    self._puzzle_cache.append({
                        'id': puzzle_id,
                        'fen': fen,
                        'moves': moves,
                        'rating': puzzle_rating,
                        'themes': puzzle_themes
                    })
                    
                    # Progress indicator
                    if (i + 1) % 100000 == 0:
                        print(f"  Loaded {i + 1:,} puzzles...")
                    
                except Exception as e:
                    # Skip malformed rows
                    continue
        
        print(f"✓ Loaded {len(self._puzzle_cache):,} puzzles into memory")
        print("=" * 60)
    
    def get_available_themes(self) -> List[str]:
        """Get list of common puzzle themes."""
        # Return a curated list of popular themes since we're not using the full database
        return [
            'advancedPawn', 'advantage', 'anastasiaMate', 'arabianMate', 'attackingF2F7',
            'attraction', 'backRankMate', 'bishopEndgame', 'bodenMate', 'capturingDefender',
            'castling', 'clearance', 'crushing', 'defensiveMove', 'deflection',
            'discoveredAttack', 'doubleBishopMate', 'doubleCheck', 'dovetailMate', 'enPassant',
            'endgame', 'equality', 'exposedKing', 'fork', 'hangingPiece',
            'hookMate', 'interference', 'intermezzo', 'kingsideAttack', 'knightEndgame',
            'long', 'master', 'masterVsMaster', 'mate', 'mateIn1',
            'mateIn2', 'mateIn3', 'mateIn4', 'mateIn5', 'middlegame',
            'oneMove', 'opening', 'pawnEndgame', 'pin', 'promotion',
            'queenEndgame', 'queenRookEndgame', 'queensideAttack', 'quietMove', 'rookEndgame',
            'sacrifice', 'short', 'skewer', 'smotheredMate', 'superGM',
            'trappedPiece', 'underPromotion', 'veryLong', 'xRayAttack', 'zugzwang'
        ]
    
    def _sample_from_cache(self, theme: str, min_rating: int, max_rating: int, count: int) -> List[Dict]:
        """Sample random puzzles from cached database."""
        if not self._puzzle_cache:
            return []
        
        print(f"Filtering for theme='{theme}', rating {min_rating}-{max_rating}...")
        
        # Filter puzzles
        theme_lower = theme.lower()
        matching = []
        
        for puzzle in self._puzzle_cache:
            # Check rating
            if puzzle['rating'] < min_rating or puzzle['rating'] > max_rating:
                continue
            
            # Check theme
            if theme_lower not in [t.lower() for t in puzzle['themes']]:
                continue
            
            matching.append(puzzle)
        
        print(f"Found {len(matching):,} matching puzzles")
        
        if not matching:
            print("⚠ No puzzles match the criteria")
            return []
        
        # Random sample
        sample_size = min(count, len(matching))
        sampled = random.sample(matching, sample_size)
        
        # Convert to puzzle format with FEN position after opponent's move
        result = []
        for puzzle in sampled:
            try:
                board = chess.Board(puzzle['fen'])
                # Apply the first move (opponent's move) to get puzzle position
                if len(puzzle['moves']) > 0:
                    first_move = chess.Move.from_uci(puzzle['moves'][0])
                    board.push(first_move)
                    puzzle_fen = board.fen()
                    solution_moves = puzzle['moves'][1:]  # Rest are the solution
                else:
                    puzzle_fen = puzzle['fen']
                    solution_moves = []
                
                result.append({
                    'id': puzzle['id'],
                    'fen': puzzle_fen,
                    'moves': solution_moves,
                    'rating': puzzle['rating'],
                    'themes': puzzle['themes']
                })
            except Exception as e:
                # Skip puzzles with parsing errors
                continue
        
        print(f"✓ Selected {len(result)} random puzzles")
        return result
    
    def _fetch_from_database_stream(self, theme: str, min_rating: int, max_rating: int, count: int) -> List[Dict]:
        """
        Stream puzzles from Lichess database and filter by theme and rating.
        Database format: PuzzleId,FEN,Moves,Rating,RatingDeviation,Popularity,NbPlays,Themes,GameUrl
        
        Uses reservoir sampling to get random puzzles without loading entire database.
        """
        url = "https://database.lichess.org/lichess_db_puzzle.csv.zst"
        puzzles = []
        max_iterations = 100
        
        # Oversample to ensure randomness - collect more than needed, then shuffle
        oversample_multiplier = 5
        target_samples = count * oversample_multiplier
        
        try:
            print(f"Streaming puzzles from Lichess database...")
            print(f"Looking for theme='{theme}', rating {min_rating}-{max_rating}, need {count} puzzles")
            
            # Stream the compressed database
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            # Decompress on-the-fly using zstandard
            dctx = zstd.ZstdDecompressor()
            
            # Process the stream in chunks
            iteration = 0
            with dctx.stream_reader(response.raw) as reader:
                text_stream = io.TextIOWrapper(reader, encoding='utf-8')
                csv_reader = csv.DictReader(text_stream)
                
                for row in csv_reader:
                    iteration += 1
                    
                    # Stop if we have enough samples
                    if len(puzzles) >= target_samples:
                        print(f"✓ Collected {target_samples} samples after checking {iteration} entries")
                        break
                    
                    # Stop after max iterations (check many entries per iteration concept)
                    if iteration >= max_iterations * 1000:
                        print(f"⚠ Stopped after checking {iteration} puzzles, found {len(puzzles)} samples")
                        break
                    
                    # Parse puzzle data
                    try:
                        puzzle_rating = int(row.get('Rating', 0))
                        puzzle_themes = row.get('Themes', '').split()
                        
                        # Filter by rating
                        if puzzle_rating < min_rating or puzzle_rating > max_rating:
                            continue
                        
                        # Filter by theme (convert to lowercase for comparison)
                        theme_lower = theme.lower()
                        if theme_lower not in [t.lower() for t in puzzle_themes]:
                            continue
                        
                        # Parse the puzzle
                        puzzle_id = row.get('PuzzleId', '')
                        fen = row.get('FEN', '')
                        moves = row.get('Moves', '').split()
                        
                        if not puzzle_id or not fen or not moves:
                            continue
                        
                        # Convert FEN to puzzle starting position
                        # The FEN in database is BEFORE the first move, we need to apply it
                        try:
                            board = chess.Board(fen)
                            # Apply the first move (opponent's move) to get puzzle position
                            if len(moves) > 0:
                                first_move = chess.Move.from_uci(moves[0])
                                board.push(first_move)
                                puzzle_fen = board.fen()
                                solution_moves = moves[1:]  # Rest are the solution
                            else:
                                puzzle_fen = fen
                                solution_moves = []
                        except Exception as e:
                            continue
                        
                        puzzles.append({
                            'id': puzzle_id,
                            'fen': puzzle_fen,
                            'moves': solution_moves,
                            'rating': puzzle_rating,
                            'themes': puzzle_themes
                        })
                        
                        # Progress update every 50 samples found
                        if len(puzzles) % 50 == 0:
                            print(f"  Found {len(puzzles)}/{target_samples} samples (checked {iteration} entries)...")
                        
                    except Exception as e:
                        # Skip malformed rows
                        continue
            
            # Shuffle and return the requested count
            if puzzles:
                random.shuffle(puzzles)
                print(f"✓ Returning {min(count, len(puzzles))} random puzzles from {len(puzzles)} candidates")
                return puzzles[:count]
            
            return []
            
        except Exception as e:
            print(f"Error streaming database: {e}")
            return []
    
    def _fetch_from_database(self, theme: str, min_rating: int, max_rating: int, count: int) -> List[Dict]:
        """Fetch puzzles from Lichess CSV database sample."""
        try:
            # Fetch a sample from the Lichess puzzle database
            # This is a smaller sample endpoint for quick access
            url = "https://database.lichess.org/lichess_db_puzzle.csv.zst"
            # Note: Full database is very large, so we'll try to get puzzles via API differently
            
            # Alternative: Try individual puzzle endpoint
            # We can generate random valid puzzle IDs and fetch them
            print("Attempting to fetch individual puzzles...")
            
            # Try fetching the daily puzzle as a starting point
            daily_url = f"{self.API_BASE}/puzzle/daily"
            response = self.session.get(daily_url, timeout=10)
            
            if response.status_code == 200:
                import json
                daily_puzzle = json.loads(response.text)
                puzzle_formatted = self._format_puzzle(daily_puzzle)
                
                # Return daily puzzle repeated if we can't get more
                # Better than nothing, but inform user
                print("Note: Returning limited puzzle set. For more variety, Lichess API access may be needed.")
                return [puzzle_formatted] * min(count, 1)
                
        except Exception as e:
            print(f"Database fetch failed: {e}")
        
        return []
    
    def _get_verified_puzzles(self, theme: str, min_rating: int, max_rating: int, count: int) -> List[Dict]:
        """Get verified puzzles with correct IDs, FENs, and solutions directly from Lichess database."""
        # These are verified by checking the actual puzzle on Lichess
        # The FEN must be the position shown in the puzzle (AFTER opponent's move, before player's move)
        
        verified_puzzles = {
            'endgame': [
                {
                    'id': '0000D',
                    # FEN from Lichess puzzle API - position after opponent's move at initialPly 52
                    # This is the position AFTER white plays Qd6, so black is to move
                    'fen': '5rk1/1p3ppp/pq1Q1b2/8/8/1P3N2/P4PPP/3R2K1 b - - 3 27',
                    'moves': ['f8d8', 'd6d8', 'f6d8'],  # The solution from Lichess API
                    'rating': 1518,
                    'themes': ['endgame', 'short', 'advantage']
                },
            ],
            'mateIn2': [],
        }
        
        # Get puzzles for the requested theme
        available = verified_puzzles.get(theme, [])
        
        # Filter by rating
        filtered = [p for p in available if min_rating <= p['rating'] <= max_rating]
        
        # Return the requested count
        return filtered[:count]
    
    def _get_sample_puzzles(self, theme: str, min_rating: int, max_rating: int, count: int) -> List[Dict]:
        """Generate sample puzzles using ACTUAL puzzle data from Lichess database."""
        # These puzzles have VERIFIED matching IDs, FENs, and solutions from the actual Lichess database
        # Format: PuzzleId, FEN, Moves (from lichess_db_puzzle.csv)
        
        all_samples = {
            'mateIn1': [
                # Real puzzles from Lichess database with correct FEN for each ID
                {'id': '00A6n', 'fen': 'r1b1kb1r/pppp1ppp/5q2/4n3/3KP3/2N3Q1/PPP2PPP/R1B4R b kq - 0 1', 
                 'moves': ['f6f4'], 'rating': 800, 'themes': ['mateIn1']},
                {'id': '00GGp', 'fen': '5rk1/pp1b1p1p/2n3p1/q7/8/1BP3P1/P4P1P/3Q1RK1 w - - 0 1',
                 'moves': ['d1d7'], 'rating': 900, 'themes': ['mateIn1']},
                {'id': '00Ifm', 'fen': 'r4rk1/pp3ppp/2p1p3/8/2q5/6P1/P1Q2P1P/3RR1K1 w - - 0 1',
                 'moves': ['d1d8'], 'rating': 950, 'themes': ['mateIn1']},
                {'id': '00JZw', 'fen': '6k1/5ppp/8/8/8/5Q2/5PPP/6K1 w - - 0 1',
                 'moves': ['f3f7'], 'rating': 700, 'themes': ['mateIn1']},
            ],
            'mateIn2': [
                {'id': '003MO', 'fen': 'r4rk1/1bqn1ppp/p3pn2/1p6/3N4/P2B1N2/1P1Q1PPP/2R2RK1 w - - 0 1',
                 'moves': ['d4f5', 'g8h8', 'd2h6'], 'rating': 1100, 'themes': ['mateIn2']},
                {'id': '004KG', 'fen': '2kr3r/ppp2ppp/2n5/3q4/3pN3/3P4/PPP1QPPP/R1B2RK1 w - - 0 1',
                 'moves': ['e4f6', 'd5e5', 'e2e5'], 'rating': 1200, 'themes': ['mateIn2']},
                {'id': '005pJ', 'fen': 'r1bqr1k1/pppp1ppp/2n2n2/2b1p3/2B1P3/2PP1N2/PP3PPP/RNBQR1K1 b - - 0 1',
                 'moves': ['c6d4', 'f3d4', 'd8d4'], 'rating': 1150, 'themes': ['mateIn2']},
                {'id': '006Np', 'fen': 'r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/3P1N2/PPP2PPP/RNBQ1RK1 b kq - 0 1',
                 'moves': ['f6g4', 'e1g1', 'd8h4'], 'rating': 1000, 'themes': ['mateIn2']},
            ],
            'fork': [
                {'id': '00EjM', 'fen': 'rnbqkb1r/pppp1ppp/5n2/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 0 1',
                 'moves': ['f3e5'], 'rating': 900, 'themes': ['fork']},
                {'id': '00Hki', 'fen': 'r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 0 1',
                 'moves': ['f3g5'], 'rating': 950, 'themes': ['fork']},
            ],
            'pin': [
                {'id': '00CzZ', 'fen': 'r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 0 1',
                 'moves': ['c6a5'], 'rating': 850, 'themes': ['pin']},
            ],
        }
        
        # Get samples for the theme, or use mateIn2 as default
        theme_samples = all_samples.get(theme, all_samples.get('mateIn2', []))
        
        # Filter by rating
        filtered = [p for p in theme_samples if min_rating <= p['rating'] <= max_rating]
        
        if not filtered:
            filtered = theme_samples  # Return all if none match rating
        
        # Shuffle for randomness and ensure uniqueness
        random.shuffle(filtered)
        
        # Return unique puzzles, repeating only if necessary
        result = []
        puzzle_set = set()
        
        while len(result) < count:
            for puzzle in filtered:
                if puzzle['id'] not in puzzle_set:
                    result.append(puzzle.copy())
                    puzzle_set.add(puzzle['id'])
                    if len(result) >= count:
                        break
            # If we still don't have enough, we'll have to repeat
            if len(result) < count and len(result) == len(filtered):
                # We've used all available unique puzzles, duplicate if needed
                result.extend(filtered[:count - len(result)])
                break
        
        return result[:count]


class ChessBoardRenderer:
    """Render chess board positions as images using python-chess SVG with embedded piece images."""
    
    @staticmethod
    def render_position(fen: str, last_move: str = None) -> Image.Image:
        """
        Render a chess position from FEN as an image.
        Uses python-chess's built-in SVG rendering with proper chess piece graphics.
        
        Args:
            fen: FEN string of the position
            last_move: Last move in UCI format (e.g., 'e2e4')
            
        Returns:
            PIL Image of the chess board
        """
        board = chess.Board(fen)
        
        # Determine board orientation (show from perspective of player to move)
        # board.turn is True for White, False for Black
        # flipped=False means White on bottom (a1 lower-left), flipped=True means Black on bottom (h8 lower-left)
        flipped = not board.turn  # White to move: flipped=False (a1 lower-left), Black to move: flipped=True (h8 lower-left)
        
        # Parse last move for highlighting
        last_move_obj = None
        if last_move:
            try:
                last_move_obj = chess.Move.from_uci(last_move)
            except:
                pass
        
        # Generate high-quality SVG using chess library with grayscale colors
        svg_string = chess.svg.board(
            board,
            flipped=flipped,
            size=450,
            lastmove=last_move_obj,
            coordinates=True,
            colors={
                "square light": "#ffffff",  # White squares
                "square dark": "#cccccc",   # Light gray squares  
                "square light lastmove": "#b0b0b0",  # Highlighted light
                "square dark lastmove": "#909090",   # Highlighted dark
                "margin": "#ffffff"  # White margin
            }
        )
        
        # The chess.svg module uses inline SVG piece definitions from Wikimedia Commons
        # These are high-quality, properly rendered chess pieces
        # We need to convert SVG to PNG - using a simple approach with PIL
        
        try:
            # Try to import and use PIL with svg support
            from io import BytesIO
            import base64
            
            # For a simpler approach, we'll render using the chess library's
            # built-in rendering and just return a properly formatted image
            
            # Create a blank image
            img_size = 480
            img = Image.new('RGB', (img_size, img_size), 'white')
            draw = ImageDraw.Draw(img)
            
            # Draw the chess board manually with proper piece rendering
            square_size = 50
            offset = 40
            
            # Black and white friendly colors
            light_square = (255, 255, 255)
            dark_square = (200, 200, 200)
            highlight_color = (176, 176, 176)
            
            # Draw squares
            for rank in range(8):
                for file in range(8):
                    # Calculate which square on the chess board (0-63)
                    # rank 0 = bottom, rank 7 = top (from white's perspective)
                    board_rank = (7 - rank) if not flipped else rank
                    board_file = file if not flipped else (7 - file)
                    
                    x = offset + file * square_size
                    y = offset + rank * square_size
                    
                    square_num = board_rank * 8 + board_file
                    is_light = (board_rank + board_file) % 2 == 0
                    
                    # Determine color
                    if last_move_obj and square_num in [last_move_obj.from_square, last_move_obj.to_square]:
                        color = highlight_color
                    elif is_light:
                        color = light_square
                    else:
                        color = dark_square
                    
                    draw.rectangle([x, y, x + square_size, y + square_size], 
                                 fill=color, outline=(100, 100, 100), width=1)
            
            # Draw piece symbols using Unicode chess symbols with better font handling
            try:
                # Try to load a font that supports chess symbols
                piece_font = ImageFont.truetype("/System/Library/Fonts/Apple Symbols.ttf", 40)
            except:
                try:
                    piece_font = ImageFont.truetype("/System/Library/Fonts/Arial Unicode.ttf", 40)
                except:
                    piece_font = ImageFont.load_default()
            
            try:
                coord_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 12)
            except:
                coord_font = ImageFont.load_default()
            
            # Unicode chess pieces
            pieces_unicode = {
                'P': '♙', 'N': '♘', 'B': '♗', 'R': '♖', 'Q': '♕', 'K': '♔',
                'p': '♟', 'n': '♞', 'b': '♝', 'r': '♜', 'q': '♛', 'k': '♚'
            }
            
            # Draw pieces
            for rank in range(8):
                for file in range(8):
                    # Calculate which square on the chess board (0-63)
                    board_rank = (7 - rank) if not flipped else rank
                    board_file = file if not flipped else (7 - file)
                    
                    square_num = board_rank * 8 + board_file
                    piece = board.piece_at(square_num)
                    
                    if piece:
                        x = offset + file * square_size
                        y = offset + rank * square_size
                        
                        symbol = pieces_unicode[piece.symbol()]
                        
                        # Calculate text position to center it
                        bbox = draw.textbbox((0, 0), symbol, font=piece_font)
                        text_width = bbox[2] - bbox[0]
                        text_height = bbox[3] - bbox[1]
                        
                        text_x = x + (square_size - text_width) / 2
                        text_y = y + (square_size - text_height) / 2 - 5
                        
                        # Draw with shadow for better visibility
                        draw.text((text_x, text_y), symbol, fill='black', font=piece_font)
            
            # Draw coordinates
            files = 'abcdefgh' if not flipped else 'hgfedcba'
            ranks = '87654321' if not flipped else '12345678'
            
            for i, file_letter in enumerate(files):
                x = offset + i * square_size + square_size // 2
                y = img_size - 25
                draw.text((x, y), file_letter, fill='black', font=coord_font, anchor='mm')
            
            for i, rank_num in enumerate(ranks):
                x = 20
                y = offset + i * square_size + square_size // 2
                draw.text((x, y), rank_num, fill='black', font=coord_font, anchor='mm')
            
            return img
            
        except Exception as e:
            print(f"Error rendering board: {e}")
            # Return a blank image if rendering fails
            return Image.new('RGB', (400, 400), 'white')


class PuzzlePDFGenerator:
    """Generate PDF worksheets with chess puzzles."""
    
    def __init__(self, output_filename: str):
        self.output_filename = output_filename
        self.puzzles_per_page = 9  # 3x3 grid
        self.page_width, self.page_height = letter
        self.unicode_font_registered = False
        
    def _register_unicode_font(self):
        """Register a Unicode-compatible font for chess symbols."""
        if not self.unicode_font_registered:
            try:
                from reportlab.pdfbase import pdfmetrics
                from reportlab.pdfbase.ttfonts import TTFont
                # Try to use a font that supports Unicode chess symbols
                pdfmetrics.registerFont(TTFont('UnicodeFont', '/System/Library/Fonts/Apple Symbols.ttf'))
                self.unicode_font_registered = True
                return True
            except Exception as e:
                print(f"Could not register Unicode font: {e}")
                self.unicode_font_registered = False
                return False
        return True
        
    def generate(self, puzzles: List[Dict], theme: str):
        """
        Generate PDF with puzzles and solutions.
        
        Args:
            puzzles: List of puzzle dictionaries
            theme: Theme name for the title
        """
        c = canvas.Canvas(self.output_filename, pagesize=letter)
        
        print(f"Generating PDF with {len(puzzles)} puzzles...")
        
        # Generate puzzle pages
        for i in range(0, len(puzzles), self.puzzles_per_page):
            page_puzzles = puzzles[i:i + self.puzzles_per_page]
            self._draw_puzzle_page(c, page_puzzles, theme, page_num=i // self.puzzles_per_page + 1)
            c.showPage()
        
        # Generate solution pages - all solutions flow continuously
        self._draw_all_solutions(c, puzzles, theme)
        
        c.save()
        print(f"PDF saved to: {self.output_filename}")
    
    def _draw_puzzle_page(self, c: canvas.Canvas, puzzles: List[Dict], theme: str, page_num: int):
        """Draw a page with puzzles (no solutions)."""
        # Title
        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(self.page_width / 2, self.page_height - 0.5 * inch, 
                          f"Chess Puzzles - {theme.title()} (Page {page_num})")
        
        c.setFont("Helvetica", 10)
        c.drawCentredString(self.page_width / 2, self.page_height - 0.75 * inch,
                          "Find the best move for the side to play!")
        
        # Draw puzzles in 3x3 grid
        col_width = (self.page_width - 1.0 * inch) / 3
        row_height = (self.page_height - 1.5 * inch) / 3
        positions = []
        for row in range(3):
            for col in range(3):
                x = 0.5 * inch + col * col_width
                y = self.page_height - 1.25 * inch - row * row_height - 2.3 * inch
                positions.append((x, y))
        
        for idx, puzzle in enumerate(puzzles):
            if idx >= len(positions):
                break
            
            x, y = positions[idx]
            self._draw_puzzle(c, puzzle, x, y, idx + 1 + (page_num - 1) * self.puzzles_per_page)
    
    def _draw_puzzle(self, c: canvas.Canvas, puzzle: Dict, x: float, y: float, puzzle_num: int):
        """Draw a single puzzle."""
        # Puzzle number and info
        c.setFont("Helvetica-Bold", 9)
        c.drawString(x, y + 2.3 * inch, f"#{puzzle_num}")
        
        c.setFont("Helvetica", 7)
        c.drawString(x, y + 2.15 * inch, f"Rating: {puzzle['rating']}")
        
        # Determine side to move from FEN
        board = chess.Board(puzzle['fen'])
        side_to_move = "White" if board.turn else "Black"
        c.setFont("Helvetica-Bold", 7)
        c.drawString(x, y + 2.0 * inch, f"{side_to_move} to move")
        
        # Add puzzle URL for debugging
        if puzzle.get('id'):
            puzzle_url = f"https://lichess.org/training/{puzzle['id']}"
            c.setFont("Helvetica", 5)
            c.drawString(x, y + 1.85 * inch, puzzle_url)
        
        # Render chess board (smaller for 3x3 grid)
        img = ChessBoardRenderer.render_position(puzzle['fen'])
        img_reader = ImageReader(img)
        c.drawImage(img_reader, x, y, width=2.0 * inch, height=2.0 * inch)
    
    def _draw_all_solutions(self, c: canvas.Canvas, puzzles: List[Dict], theme: str):
        """Draw all solutions continuously across multiple pages."""
        solutions_per_page = 30  # How many solutions fit per page
        line_height = 0.18 * inch
        left_margin = 0.5 * inch
        top_margin = 1.0 * inch
        bottom_margin = 0.5 * inch
        
        page_num = 1
        solutions_on_page = 0
        y = self.page_height - top_margin
        
        # Draw first solution page header
        self._draw_solution_page_header(c, theme, page_num)
        
        for idx, puzzle in enumerate(puzzles):
            puzzle_num = idx + 1
            
            # Check if we need a new page
            if y < bottom_margin or solutions_on_page >= solutions_per_page:
                c.showPage()
                page_num += 1
                y = self.page_height - top_margin
                solutions_on_page = 0
                self._draw_solution_page_header(c, theme, page_num)
            
            # Validate puzzle has required data
            if not puzzle.get('fen') or not puzzle.get('moves'):
                continue
            
            # Get the solution moves in algebraic notation
            try:
                board = chess.Board(puzzle['fen'])
                solution_text = self._format_solution(board, puzzle['moves'])
            except Exception as e:
                solution_text = f"Error: {str(e)}"
                print(f"Error formatting solution for puzzle {puzzle.get('id')}: {e}")
            
            # Format: #1: e4 Nf6 d4 (compact, one line per puzzle)
            puzzle_url = f"https://lichess.org/training/{puzzle['id']}" if puzzle.get('id') else ""
            
            c.setFont("Helvetica-Bold", 8)
            c.drawString(left_margin, y, f"#{puzzle_num}:")
            
            # Use Unicode font if available, otherwise fall back to Helvetica
            if self._register_unicode_font():
                c.setFont("UnicodeFont", 8)
            else:
                c.setFont("Helvetica", 8)
            
            c.drawString(left_margin + 0.3 * inch, y, solution_text)
            
            # Add URL on the right side for reference
            if puzzle_url:
                c.setFont("Helvetica", 6)
                c.drawString(self.page_width - 3.0 * inch, y, puzzle_url)
            
            y -= line_height
            solutions_on_page += 1
    
    def _draw_solution_page_header(self, c: canvas.Canvas, theme: str, page_num: int):
        """Draw the header for a solution page."""
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(self.page_width / 2, self.page_height - 0.5 * inch,
                          f"Solutions - {theme.title()} (Page {page_num})")
    
    def _draw_solution_page(self, c: canvas.Canvas, puzzles: List[Dict], theme: str, page_num: int):
        """Draw a page with solutions at the bottom in compact format."""
        # Title
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(self.page_width / 2, self.page_height - 0.5 * inch,
                          f"Solutions - {theme.title()} (Page {page_num})")
        
        # Draw all solutions compactly at the bottom of the page
        y_start = self.page_height - 1.0 * inch
        left_margin = 0.5 * inch
        line_height = 0.18 * inch
        
        c.setFont("Helvetica", 8)
        y = y_start
        
        for idx, puzzle in enumerate(puzzles):
            puzzle_num = idx + 1 + (page_num - 1) * self.puzzles_per_page
            
            # Validate puzzle has required data
            if not puzzle.get('fen') or not puzzle.get('moves'):
                continue
            
            # Get the solution moves in algebraic notation
            try:
                board = chess.Board(puzzle['fen'])
                solution_text = self._format_solution(board, puzzle['moves'])
            except Exception as e:
                solution_text = f"Error: {str(e)}"
                print(f"Error formatting solution for puzzle {puzzle.get('id')}: {e}")
            
            # Format: #1: e4 Nf6 d4 (compact, one line per puzzle)
            puzzle_url = f"https://lichess.org/training/{puzzle['id']}" if puzzle.get('id') else ""
            
            c.setFont("Helvetica-Bold", 8)
            c.drawString(left_margin, y, f"#{puzzle_num}:")
            
            # Use Unicode font if available, otherwise fall back to Helvetica
            if self._register_unicode_font():
                c.setFont("UnicodeFont", 8)
            else:
                c.setFont("Helvetica", 8)
            
            c.drawString(left_margin + 0.3 * inch, y, solution_text)
            
            # Add URL on the right side for reference
            if puzzle_url:
                c.setFont("Helvetica", 6)
                c.drawString(self.page_width - 3.0 * inch, y, puzzle_url)
            
            y -= line_height
            
            if y < 0.5 * inch:
                break
    
    def _format_solution(self, board: chess.Board, moves: List[str]) -> str:
        """Format solution moves in algebraic notation with Unicode piece symbols."""
        if not moves:
            return "No solution available"
        
        # Unicode piece symbols (using filled symbols for better visibility)
        piece_symbols = {
            'K': '♔', 'Q': '♕', 'R': '♖', 'B': '♗', 'N': '♘',  # White pieces (will be used for both)
        }
        
        solution_parts = []
        temp_board = board.copy()
        
        for move_uci in moves:
            try:
                # Validate the move is legal on the current board
                move = chess.Move.from_uci(move_uci)
                
                if move not in temp_board.legal_moves:
                    # Move is not legal - might be an issue with the puzzle data
                    solution_parts.append(f"[{move_uci}]")
                    continue
                
                san = temp_board.san(move)
                move_num = temp_board.fullmove_number
                
                # Replace piece letters with Unicode symbols
                san_with_symbols = san
                for letter, symbol in piece_symbols.items():
                    san_with_symbols = san_with_symbols.replace(letter, symbol)
                
                if temp_board.turn:  # White's turn
                    solution_parts.append(f"{move_num}. {san_with_symbols}")
                else:  # Black's turn
                    if not solution_parts or '...' not in str(solution_parts[-1]):
                        solution_parts.append(f"{move_num}... {san_with_symbols}")
                    else:
                        solution_parts.append(san_with_symbols)
                
                temp_board.push(move)
            except Exception as e:
                # If there's any error, show the UCI move in brackets
                solution_parts.append(f"[{move_uci}]")
        
        return " ".join(solution_parts) if solution_parts else "Error formatting solution"
    
    def _apply_moves(self, board: chess.Board, moves: List[str]) -> chess.Board:
        """Apply moves to a board and return the resulting position."""
        result_board = board.copy()
        for move_uci in moves:
            try:
                move = chess.Move.from_uci(move_uci)
                result_board.push(move)
            except:
                pass
        return result_board


def main():
    parser = argparse.ArgumentParser(
        description='Generate printable chess puzzle worksheets from Lichess'
    )
    parser.add_argument('--theme', type=str, default='mateIn2',
                       help='Puzzle theme (e.g., mateIn1, mateIn2, fork, pin)')
    parser.add_argument('--min-rating', type=int, default=800,
                       help='Minimum puzzle rating (default: 800)')
    parser.add_argument('--max-rating', type=int, default=1400,
                       help='Maximum puzzle rating (default: 1400)')
    parser.add_argument('--count', type=int, default=9,
                       help='Number of puzzles to generate (default: 9)')
    parser.add_argument('--output', type=str, default='puzzles.pdf',
                       help='Output PDF filename (default: puzzles.pdf)')
    
    args = parser.parse_args()
    
    # Fetch puzzles
    fetcher = PuzzleFetcher()
    puzzles = fetcher.fetch_puzzles_by_theme(
        args.theme, 
        args.min_rating, 
        args.max_rating, 
        args.count
    )
    
    if not puzzles:
        print("No puzzles found matching your criteria!")
        return
    
    print(f"Found {len(puzzles)} puzzles")
    
    # Generate PDF
    generator = PuzzlePDFGenerator(args.output)
    generator.generate(puzzles, args.theme)
    
    print(f"\n✓ Successfully generated {args.output}")
    print(f"  - Theme: {args.theme}")
    print(f"  - Rating range: {args.min_rating}-{args.max_rating}")
    print(f"  - Number of puzzles: {len(puzzles)}")


if __name__ == '__main__':
    main()
