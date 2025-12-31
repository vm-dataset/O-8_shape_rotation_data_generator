"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                           YOUR TASK GENERATOR                                 ║
║                                                                               ║
║  CUSTOMIZE THIS FILE to implement your data generation logic.                 ║
║  Replace the example implementation with your own task.                       ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import random
import tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

from core import BaseGenerator, TaskPair, ImageRenderer
from core.video_utils import VideoGenerator
from .config import TaskConfig
from .prompts import get_prompt

# Check if chess library is available
import importlib.util

CHESS_AVAILABLE = importlib.util.find_spec("chess") is not None

if CHESS_AVAILABLE:
    import chess
    import chess.svg
    
    # Check if cairosvg is available for high-quality SVG rendering
    CAIROSVG_AVAILABLE = importlib.util.find_spec("cairosvg") is not None
    if CAIROSVG_AVAILABLE:
        import cairosvg
else:
    chess = None
    CAIROSVG_AVAILABLE = False
    print("⚠️  Warning: python-chess not installed. Using fallback templates.")
    print("   Install with: pip install python-chess")


class TaskGenerator(BaseGenerator):
    """
    Your custom task generator.
    
    IMPLEMENT THIS CLASS for your specific task.
    
    Required:
        - generate_task_pair(task_id) -> TaskPair
    
    The base class provides:
        - self.config: Your TaskConfig instance
        - generate_dataset(): Loops and calls generate_task_pair() for each sample
    """
    
    def __init__(self, config: TaskConfig):
        super().__init__(config)
        self.renderer = ImageRenderer(image_size=config.image_size)
        
        # Initialize video generator if enabled (using mp4 format)
        self.video_generator = None
        if config.generate_videos and VideoGenerator.is_available():
            self.video_generator = VideoGenerator(fps=config.video_fps, output_format="mp4")
        
        # Fallback templates if chess library not installed
        self.use_templates = not CHESS_AVAILABLE
        if self.use_templates:
            self.templates = self._get_fallback_templates()
    
    def generate_task_pair(self, task_id: str) -> TaskPair:
        """Generate one task pair."""
        
        # Generate task data
        if self.use_templates:
            task_data = random.choice(self.templates)
        else:
            task_data = self._generate_task_data()
        
        # Render images
        first_image = self._render_initial_state(task_data)
        final_image = self._render_final_state(task_data)
        
        # Generate video (optional)
        video_path = None
        if self.config.generate_videos and self.video_generator:
            video_path = self._generate_video(first_image, final_image, task_id, task_data)
        
        # Select prompt
        prompt = get_prompt(task_data.get("type", "default"))
        
        return TaskPair(
            task_id=task_id,
            domain=self.config.domain,
            prompt=prompt,
            first_image=first_image,
            final_image=final_image,
            ground_truth_video=video_path
        )
    
    # ══════════════════════════════════════════════════════════════════════════
    #  TASK-SPECIFIC METHODS
    # ══════════════════════════════════════════════════════════════════════════
    
    def _generate_task_data(self) -> dict:
        """Generate mate-in-1 position using chess library."""
        generators = [
            self._gen_back_rank_mate,
            self._gen_queen_mate,
            self._gen_rook_mate,
        ]
        
        for _ in range(10):  # Try up to 10 times
            gen_func = random.choice(generators)
            position = gen_func()
            if position and self._validate_mate(position):
                return position
        
        # Fallback to template
        return random.choice(self._get_fallback_templates())
    
    def _render_initial_state(self, task_data: dict) -> Image.Image:
        """Render chess position from FEN."""
        return self._render_board(task_data["fen"])
    
    def _render_final_state(self, task_data: dict) -> Image.Image:
        """Render position after mate move."""
        if CHESS_AVAILABLE:
            board = chess.Board(task_data["fen"])
            move = chess.Move.from_uci(task_data["solution"])
            board.push(move)
            return self._render_board(board.fen())
        else:
            # Fallback: use pre-computed final FEN if available
            final_fen = task_data.get("final_fen", task_data["fen"])
            return self._render_board(final_fen)
    
    def _generate_video(
        self,
        first_image: Image.Image,
        final_image: Image.Image,
        task_id: str,
        task_data: dict
    ) -> str:
        """Generate ground truth video with piece sliding and fading."""
        temp_dir = Path(tempfile.gettempdir()) / f"{self.config.domain}_videos"
        temp_dir.mkdir(parents=True, exist_ok=True)
        video_path = temp_dir / f"{task_id}_ground_truth.mp4"
        
        # For chess, create custom animation with piece fading
        frames = self._create_chess_animation_frames(task_data)
        
        result = self.video_generator.create_video_from_frames(
            frames,
            video_path
        )
        
        return str(result) if result else None
    
    def _create_chess_animation_frames(
        self,
        task_data: dict,
        hold_frames: int = 5,
        transition_frames: int = 25
    ) -> list:
        """
        Create animation frames where the moving chess piece slides across the board.
        
        The piece slides smoothly from start to end position.
        NO fading - the piece stays fully visible (100% opacity) the entire time.
        """
        if not CHESS_AVAILABLE:
            # Fallback: simple crossfade
            start_img = self._render_board(task_data["fen"])
            end_img = self._render_final_state(task_data)
            return [start_img] * hold_frames + [end_img] * hold_frames
        
        frames = []
        fen = task_data["fen"]
        move_uci = task_data["solution"]
        
        # Parse the move
        board = chess.Board(fen)
        move = chess.Move.from_uci(move_uci)
        from_square = move.from_square
        to_square = move.to_square
        moving_piece = board.piece_at(from_square)
        
        # Hold initial position
        for _ in range(hold_frames):
            frames.append(self._render_board(fen))
        
        # Create transition frames
        board_size = self.config.image_size[0]
        square_size = board_size // 8
        
        # Calculate start and end positions in pixels
        from_file = chess.square_file(from_square)
        from_rank = chess.square_rank(from_square)
        to_file = chess.square_file(to_square)
        to_rank = chess.square_rank(to_square)
        
        # Pixel coordinates (center of square)
        start_x = from_file * square_size + square_size // 2
        start_y = (7 - from_rank) * square_size + square_size // 2
        end_x = to_file * square_size + square_size // 2
        end_y = (7 - to_rank) * square_size + square_size // 2
        
        # PRE-RENDER the piece ONCE to keep it pixel-perfect consistent
        piece_image = self._render_single_piece(moving_piece, square_size)
        
        for i in range(transition_frames):
            progress = i / (transition_frames - 1) if transition_frames > 1 else 1.0
            
            # Calculate piece position
            current_x = start_x + (end_x - start_x) * progress
            current_y = start_y + (end_y - start_y) * progress
            
            # Render frame with pre-rendered piece at intermediate position
            frame = self._render_frame_with_moving_piece(
                board, from_square, to_square, piece_image,
                current_x, current_y, square_size
            )
            frames.append(frame)
        
        # Hold final position
        board.push(move)
        for _ in range(hold_frames):
            frames.append(self._render_board(board.fen()))
        
        return frames
    
    def _render_frame_with_moving_piece(
        self,
        board: 'chess.Board',
        from_square: int,
        to_square: int,
        piece_image: Image.Image,
        piece_x: float,
        piece_y: float,
        square_size: int
    ) -> Image.Image:
        """Render a single frame with the pre-rendered moving piece at a specific position."""
        # Create a modified board without the moving piece
        board_copy = board.copy()
        board_copy.remove_piece_at(from_square)
        
        # Render the board without the moving piece
        base_image = self._render_board(board_copy.fen())
        
        # Composite the pre-rendered piece onto the board
        result = base_image.convert('RGBA')
        piece_width, piece_height = piece_image.size
        paste_x = int(piece_x - piece_width // 2)
        paste_y = int(piece_y - piece_height // 2)
        result.paste(piece_image, (paste_x, paste_y), piece_image)
        
        return result.convert('RGB')
    
    def _render_single_piece(self, piece: 'chess.Piece', square_size: int) -> Image.Image:
        """Render a single chess piece."""
        img = Image.new("RGBA", (square_size, square_size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        font = self._get_chess_font(square_size)
        
        unicode_map = {
            'P': '\u2659', 'N': '\u2658', 'B': '\u2657', 
            'R': '\u2656', 'Q': '\u2655', 'K': '\u2654',
            'p': '\u265F', 'n': '\u265E', 'b': '\u265D', 
            'r': '\u265C', 'q': '\u265B', 'k': '\u265A',
        }
        
        sym = piece.symbol()
        label = unicode_map.get(sym, sym.upper())
        
        # Get text bounds for centering
        bbox = draw.textbbox((0, 0), label, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        
        x = (square_size - w) // 2
        y = (square_size - h) // 2
        
        # Draw with outline for contrast
        fill_color = (245, 245, 245) if piece.color else (20, 20, 20)
        outline_color = (0, 0, 0) if piece.color else (255, 255, 255)
        
        # Draw outline
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                draw.text((x + dx, y + dy), label, font=font, fill=outline_color)
        
        # Draw piece
        draw.text((x, y), label, font=font, fill=fill_color)
        
        return img
    
    # ══════════════════════════════════════════════════════════════════════════
    #  CHESS GENERATION HELPERS
    # ══════════════════════════════════════════════════════════════════════════
    
    def _gen_back_rank_mate(self) -> dict:
        """Generate back-rank mate pattern."""
        fens = [
            "7k/5ppp/8/8/8/8/8/R6K w - - 0 1",
            "7k/6pp/8/8/8/8/8/Q6K w - - 0 1",
            "6k1/5ppp/8/8/8/8/8/R6K w - - 0 1",
        ]
        
        fen = random.choice(fens)
        board = chess.Board(fen)
        
        for move in board.legal_moves:
            board.push(move)
            if board.is_checkmate():
                solution = board.pop().uci()
                return {
                    "fen": fen,
                    "solution": solution,
                    "type": "back_rank",
                    "difficulty": "easy",
                }
            board.pop()
        
        return None
    
    def _gen_queen_mate(self) -> dict:
        """Generate queen mate pattern."""
        fens = [
            "7k/8/6K1/5Q2/8/8/8/8 w - - 0 1",
            "7k/8/5K2/8/4Q3/8/8/8 w - - 0 1",
        ]
        
        fen = random.choice(fens)
        board = chess.Board(fen)
        
        for move in board.legal_moves:
            board.push(move)
            if board.is_checkmate():
                solution = board.pop().uci()
                return {
                    "fen": fen,
                    "solution": solution,
                    "type": "queen_mate",
                    "difficulty": "easy",
                }
            board.pop()
        
        return None
    
    def _gen_rook_mate(self) -> dict:
        """Generate rook mate pattern."""
        fens = [
            "7k/8/5K2/8/8/8/8/R7 w - - 0 1",
            "7k/8/6K1/8/8/8/8/7R w - - 0 1",
        ]
        
        fen = random.choice(fens)
        board = chess.Board(fen)
        
        for move in board.legal_moves:
            board.push(move)
            if board.is_checkmate():
                solution = board.pop().uci()
                return {
                    "fen": fen,
                    "solution": solution,
                    "type": "rook_mate",
                    "difficulty": "easy",
                }
            board.pop()
        
        return None
    
    def _validate_mate(self, position: dict) -> bool:
        """Validate that the position is a valid mate-in-1."""
        if not position:
            return False
        
        board = chess.Board(position["fen"])
        move = chess.Move.from_uci(position["solution"])
        
        if move not in board.legal_moves:
            return False
        
        board.push(move)
        return board.is_checkmate()
    
    # ══════════════════════════════════════════════════════════════════════════
    #  BOARD RENDERING
    # ══════════════════════════════════════════════════════════════════════════
    
    def _render_board(self, fen: str) -> Image.Image:
        """
        Render chess board from FEN string.
        
        Uses chess.svg + cairosvg for best quality, falls back to PIL rendering.
        """
        board_size = self.config.image_size[0]
        
        # Method 1: Use chess.svg + cairosvg for high quality
        if CHESS_AVAILABLE and CAIROSVG_AVAILABLE:
            board = chess.Board(fen)
            svg_content = chess.svg.board(board=board, size=board_size)
            
            # Convert SVG to PNG via cairosvg
            import io
            png_data = cairosvg.svg2png(bytestring=svg_content.encode('utf-8'))
            return Image.open(io.BytesIO(png_data)).convert('RGB')
        
        # Method 2: PIL-based rendering (fallback)
        return self._render_board_pil(fen, board_size)
    
    def _render_board_pil(self, fen: str, board_size: int = 400) -> Image.Image:
        """
        Render chess board using PIL (fallback implementation).
        """
        img = Image.new("RGB", (board_size, board_size), color="white")
        draw = ImageDraw.Draw(img)
        
        square_px = board_size // 8
        light = (240, 217, 181)
        dark = (181, 136, 99)
        
        # Load font for chess pieces
        font = self._get_chess_font(square_px)
        
        # Draw squares
        for rank in range(8):
            for file_idx in range(8):
                x0 = file_idx * square_px
                y0 = (7 - rank) * square_px  # rank 0 at bottom
                color = light if (rank + file_idx) % 2 == 0 else dark
                draw.rectangle([x0, y0, x0 + square_px, y0 + square_px], fill=color)
        
        # Unicode chess piece glyphs
        unicode_map = {
            'P': '\u2659', 'N': '\u2658', 'B': '\u2657', 
            'R': '\u2656', 'Q': '\u2655', 'K': '\u2654',
            'p': '\u265F', 'n': '\u265E', 'b': '\u265D', 
            'r': '\u265C', 'q': '\u265B', 'k': '\u265A',
        }
        
        # Draw pieces
        if CHESS_AVAILABLE:
            board = chess.Board(fen)
            piece_map = board.piece_map()
            
            for sq, piece in piece_map.items():
                file_idx = chess.square_file(sq)
                rank = chess.square_rank(sq)
                x_center = file_idx * square_px + square_px // 2
                y_center = (7 - rank) * square_px + square_px // 2
                
                sym = piece.symbol()
                label = unicode_map.get(sym, sym.upper())
                
                # Get text bounds for centering
                bbox = draw.textbbox((0, 0), label, font=font)
                w = bbox[2] - bbox[0]
                h = bbox[3] - bbox[1]
                
                x = x_center - w / 2
                y = y_center - h / 2
                
                # Draw with outline for contrast
                fill_color = (245, 245, 245) if piece.color else (20, 20, 20)
                outline_color = (0, 0, 0) if piece.color else (255, 255, 255)
                
                # Draw outline
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        draw.text((x + dx, y + dy), label, font=font, fill=outline_color)
                
                # Draw piece
                draw.text((x, y), label, font=font, fill=fill_color)
        else:
            self._draw_pieces_from_fen_pil(draw, fen, square_px, font, unicode_map)
        
        return img
    
    def _get_chess_font(self, square_px: int) -> ImageFont.FreeTypeFont:
        """Get a font for rendering chess pieces."""
        font_size = int(square_px * 0.75)
        
        # Try common fonts that support chess Unicode glyphs
        font_names = [
            "DejaVuSans.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
            "/Library/Fonts/Arial Unicode.ttf",
            "Arial Unicode.ttf",
            "Segoe UI Symbol",
        ]
        
        for font_name in font_names:
            try:
                return ImageFont.truetype(font_name, font_size)
            except (OSError, IOError):
                continue
        
        # Fallback to default
        return ImageFont.load_default()
    
    def _draw_pieces_from_fen_pil(
        self,
        draw: ImageDraw.Draw,
        fen: str,
        square_px: int,
        font: ImageFont.FreeTypeFont,
        unicode_map: dict
    ) -> None:
        """Draw pieces from FEN when chess library is not available."""
        board_fen = fen.split()[0]
        ranks = board_fen.split('/')
        
        for rank_idx, rank_str in enumerate(ranks):
            file_idx = 0
            for char in rank_str:
                if char.isdigit():
                    file_idx += int(char)
                elif char in unicode_map:
                    x_center = file_idx * square_px + square_px // 2
                    y_center = rank_idx * square_px + square_px // 2
                    
                    label = unicode_map[char]
                    bbox = draw.textbbox((0, 0), label, font=font)
                    w = bbox[2] - bbox[0]
                    h = bbox[3] - bbox[1]
                    
                    x = x_center - w / 2
                    y = y_center - h / 2
                    
                    # White pieces are uppercase
                    is_white = char.isupper()
                    fill_color = (245, 245, 245) if is_white else (20, 20, 20)
                    outline_color = (0, 0, 0) if is_white else (255, 255, 255)
                    
                    for dx in (-1, 0, 1):
                        for dy in (-1, 0, 1):
                            if dx == 0 and dy == 0:
                                continue
                            draw.text((x + dx, y + dy), label, font=font, fill=outline_color)
                    
                    draw.text((x, y), label, font=font, fill=fill_color)
                    file_idx += 1
    
    def _get_fallback_templates(self) -> list:
        """Fallback templates when chess library not available."""
        return [
            {
                "fen": "7k/5ppp/8/8/8/8/8/R6K w - - 0 1",
                "final_fen": "R6k/5ppp/8/8/8/8/8/7K b - - 1 1",  # Rook on a8, checkmate
                "solution": "a1a8",
                "type": "back_rank",
                "difficulty": "easy"
            },
            {
                "fen": "7k/8/6K1/5Q2/8/8/8/8 w - - 0 1",
                "final_fen": "7k/6Q1/6K1/8/8/8/8/8 b - - 1 1",  # Queen on g7, checkmate
                "solution": "f5g7",
                "type": "queen_mate",
                "difficulty": "easy"
            },
            {
                "fen": "7k/8/5K2/8/8/8/8/R7 w - - 0 1",
                "final_fen": "7k/8/5K2/8/8/8/8/7R b - - 1 1",  # Rook on h1, checkmate
                "solution": "a1h1",
                "type": "rook_mate",
                "difficulty": "easy"
            },
        ]
