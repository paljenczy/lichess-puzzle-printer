# Lichess Puzzle Printer

Generate printable chess puzzle worksheets using [Lichess.org](https://lichess.org)'s free and open puzzle database.

Perfect for parents, teachers, and coaches who want to create custom chess practice sheets for kids!

## Features

- 🎯 **Modern Web UI** - Beautiful, easy-to-use browser interface
- 🎨 **60+ Puzzle Themes** - Mate in 2, fork, pin, skewer, and many more
- 📊 **Difficulty Levels** - Filter by rating (500-3000+)
- 📄 **Professional PDFs** - 9 puzzles per page in clear 3x3 grid layout
- ✅ **Complete Solutions** - Detailed solutions with chess notation
- 🔄 **Random Selection** - Different puzzles every time
- 🎲 **5.6M Puzzles** - Powered by Lichess's complete puzzle database
- 🆓 **Completely Free** - No ads, no tracking, no sign-up required

## Quick Start

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)

### Installation

1. Clone or download this repository:
```bash
git clone https://github.com/yourusername/lichess-puzzle-printer.git
cd lichess-puzzle-printer
```

2. Create a virtual environment (recommended):
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the app:
```bash
python app.py
```

On first run, the app will download the Lichess puzzle database (~266 MB). This takes 1-5 minutes and only happens once.

### Running the App

#### Web Interface (Recommended)

```bash
python app.py
```

Then open your browser to `http://localhost:5000`

#### Command Line

```bash
python puzzle_printer.py --theme mateIn2 --min-rating 800 --max-rating 1400 --count 36 --output puzzles.pdf
```

## Usage Guide

### First Run

On first launch, the app will automatically download Lichess's puzzle database:
- **Download**: ~266 MB compressed
- **Uncompressed**: ~980 MB on disk
- **Time**: 1-5 minutes depending on your connection
- **One-time only**: The database is cached locally and reused

The database gives you instant access to 5.6 million puzzles offline!

### Generating Puzzles

1. **Select Theme** - Choose from 60+ puzzle types
2. **Set Difficulty** - Pick a rating range appropriate for the player's level
3. **Choose Count** - Default is 36 puzzles (4 pages)
4. **Generate** - Click the button and your PDF downloads automatically

### Rating Guide

- **600-1000**: Beginner (learning basic tactics)
- **1000-1400**: Intermediate (solid fundamental tactics)
- **1400-1800**: Advanced (complex combinations)
- **1800+**: Expert (tournament-level tactics)

### Popular Themes for Kids

- `mateIn1` - Find checkmate in one move
- `mateIn2` - Find checkmate in two moves
- `fork` - Attack two pieces simultaneously
- `pin` - Pin opponent's piece
- `hangingPiece` - Capture undefended pieces
- `discoveredAttack` - Reveal hidden attacks
- `skewer` - Attack through a more valuable piece

### Command Line Options

- `--theme`: Puzzle theme code (e.g., mateIn2, fork, pin)
- `--min-rating`: Minimum puzzle rating (default: 800)
- `--max-rating`: Maximum puzzle rating (default: 1400)
- `--count`: Number of puzzles to generate (default: 12)
- `--output`: Output PDF filename (default: puzzles.pdf)

## How It Works

1. **Downloads** Lichess's open puzzle database (one-time, ~980 MB)
2. **Filters** puzzles by your selected theme and difficulty range
3. **Randomly samples** to ensure variety on each generation
4. **Renders** chess positions with proper board orientation
5. **Generates** a professional PDF with puzzles and solutions

## Technical Details

- **Backend**: Python with Flask web framework
- **Chess Logic**: python-chess library for position validation
- **PDF Generation**: ReportLab for document creation
- **Database**: Lichess open puzzle database (5.6M puzzles, cached locally)
- **Compression**: zstandard for efficient database storage
- **Storage**: ~1 GB for local database cache (one-time download)

## License & Attribution

This project is licensed under the **MIT License** - see [LICENSE](LICENSE) file for details.

### Puzzle Data

All puzzle data comes from [Lichess.org](https://lichess.org), which provides it under:
- **Database License**: Creative Commons CC0 1.0 Universal (Public Domain)
- **Lichess Software**: GNU Affero General Public License v3.0+

**Important**: Puzzle theme descriptions (`translation/source/puzzleTheme.xml`) are licensed under **CC0 1.0** by Lichess contributors.

### Proper Attribution

This app includes prominent attribution to Lichess.org:
- "Powered by Lichess.org" in the web interface
- Puzzle URLs included in generated PDFs
- This README credits Lichess as the data source

### Lichess Terms Compliance

This project complies with [Lichess Terms of Service](https://lichess.org/terms-of-service):
- ✅ Non-commercial use of their services and database
- ✅ Proper attribution to Lichess.org
- ✅ No modification of puzzle data
- ✅ Respects their open-source philosophy
- ✅ No commercial monetization

## Publishing & Distribution

### Recommended Platforms

**For Public Use:**
1. **GitHub** - Host the code publicly with clear Lichess attribution
2. **Heroku/Railway/Render** - Deploy free web hosting
3. **Docker Hub** - Containerized deployment
4. **Python Package Index (PyPI)** - Distribute as installable package

### Best Practices

**Legal & Ethical:**
- ✅ Keep it 100% free (respect Lichess's free/libre ethos)
- ✅ Maintain clear attribution to Lichess.org
- ✅ Include LICENSE file (MIT recommended for your code)
- ✅ Note Lichess data license (CC0 1.0) in documentation
- ✅ Link to Lichess.org for users to explore more
- ✅ Consider adding a "Support Lichess" link to their patron page

**Technical:**
- ✅ Clear installation instructions
- ✅ Document database download (first-time setup)
- ✅ Include requirements.txt with exact versions
- ✅ Add .gitignore for lichess_puzzles.csv (too large for git)
- ✅ Provide Docker support for easy deployment
- ✅ Include troubleshooting guide

**Community:**
- ✅ Accept contributions via pull requests
- ✅ Respond to issues and feedback
- ✅ Share on chess forums/communities
- ✅ Consider internationalization (i18n)

### Deployment Example (Heroku)

```bash
# Add Procfile
echo "web: python app.py" > Procfile

# Add runtime.txt
echo "python-3.12.0" > runtime.txt

# Deploy
heroku create chess-puzzle-printer
git push heroku main
```

## Contributing

Contributions are welcome! This is an open-source project aimed at helping chess education.

### Ways to Contribute
- Report bugs or suggest features via GitHub Issues
- Submit pull requests for improvements
- Translate the interface to other languages
- Share with other chess parents and teachers
- Improve documentation

## Support Lichess

This app is powered by Lichess's incredible free and open database. If you find this useful, please consider:

- **Donating to Lichess**: [lichess.org/patron](https://lichess.org/patron)
- **Using Lichess**: [lichess.org](https://lichess.org) for playing and training
- **Spreading the word**: Tell other chess players about Lichess

Lichess is a charitable organization that keeps chess free for everyone!

## Acknowledgments

- **Lichess.org** - For providing free access to 5.6M puzzles
- **python-chess** - Excellent chess library by Niklas Fiekas
- **ReportLab** - PDF generation toolkit
- The open-source chess community

## Questions?

- **Issues**: Open a GitHub issue
- **Lichess**: Check [lichess.org/faq](https://lichess.org/faq)
- **Chess.com vs Lichess**: This uses Lichess data exclusively

---

**Note**: This is an independent project, not officially affiliated with Lichess.org. All puzzle data is used in accordance with Lichess's open data policy and terms of service.
