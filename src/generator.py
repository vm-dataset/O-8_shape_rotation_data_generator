"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                           SHAPE ROTATION TASK GENERATOR                       ║
║                                                                               ║
║  Generates analog shape rotation tasks (A:B :: C:?)                           ║
║  Example: upright square → 45° rotated square, upright triangle → 45° triangle║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import random
import tempfile
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from typing import Dict, List, Tuple, Any

from core import BaseGenerator, TaskPair, ImageRenderer
from core.video_utils import VideoGenerator
from .config import TaskConfig
from .prompts import get_prompt


class TaskGenerator(BaseGenerator):
    """
    Shape rotation task generator.
    
    Creates visual analogies in the format A:B :: C:?
    where shapes undergo rotation transformations.
    """
    
    def __init__(self, config: TaskConfig):
        super().__init__(config)
        self.renderer = ImageRenderer(image_size=config.image_size)
        
        # Initialize video generator if enabled
        self.video_generator = None
        if config.generate_videos and VideoGenerator.is_available():
            self.video_generator = VideoGenerator(fps=config.video_fps, output_format="mp4")
        
        # Shape definitions - expanded set of shapes that show clear rotation effects
        self.base_shapes = [
            "square", "triangle", "diamond", "pentagon", "hexagon",
            "rectangle", "star", "heart", "arrow", "cross", "octagon",
            "trapezoid", "rhombus", "plus", "minus", "L_shape", "T_shape",
            "parallelogram", "kite", "chevron"
        ]
        
        # Rotation angles in degrees - expanded set with more granular rotations
        self.rotation_angles = [
            15, 22.5, 30, 37.5, 45, 52.5, 60, 67.5, 75, 82.5, 90, 97.5,
            105, 112.5, 120, 127.5, 135, 142.5, 150, 157.5, 165, 172.5,
            180, 187.5, 195, 202.5, 210, 217.5, 225, 232.5, 240, 247.5,
            255, 262.5, 270, 277.5, 285, 292.5, 300, 307.5, 315, 322.5,
            330, 337.5, 345, 352.5
        ]
        
        # Single color for all shapes (focus on rotation, not color)
        self.shape_color = (70, 130, 180)  # Blue
        
        # Track generated combinations to prevent duplicates
        self.generated_combinations = set()
    
    def generate_task_pair(self, task_id: str) -> TaskPair:
        """Generate one shape rotation task pair."""
        
        # Generate task data
        task_data = self._generate_task_data()
        
        # Render images
        first_image = self._render_initial_state(task_data)
        final_image = self._render_final_state(task_data)
        
        # Generate video (optional)
        video_path = None
        if self.config.generate_videos and self.video_generator:
            video_path = self._generate_video(first_image, final_image, task_id, task_data)
        
        # Select prompt
        prompt = get_prompt(task_data.get("transformation_type", "default"))
        
        return TaskPair(
            task_id=task_id,
            domain=self.config.domain,
            prompt=prompt,
            first_image=first_image,
            final_image=final_image,
            ground_truth_video=video_path
        )
    
    # ══════════════════════════════════════════════════════════════════════════
    #  TASK DATA GENERATION
    # ══════════════════════════════════════════════════════════════════════════
    
    def _generate_task_data(self) -> Dict[str, Any]:
        """Generate rotation transformation task data with duplicate prevention."""
        
        # Calculate total possible unique combinations
        num_shapes = len(self.base_shapes)
        num_rotation_angles = len(self.rotation_angles)
        max_unique_combinations = num_shapes * (num_shapes - 1) * num_rotation_angles
        
        # If we haven't exhausted all combinations, ensure uniqueness
        if len(self.generated_combinations) < max_unique_combinations:
            max_attempts = 1000  # Increase attempts for better coverage
            for attempt in range(max_attempts):
                # Select two different shapes for the analogy
                shape_a, shape_c = random.sample(self.base_shapes, 2)
                # Select rotation angle
                rotation_angle = random.choice(self.rotation_angles)
                
                # Create a unique identifier for this combination
                combination_key = (shape_a, shape_c, rotation_angle)
                
                # Check if this combination has been used before
                if combination_key not in self.generated_combinations:
                    self.generated_combinations.add(combination_key)
                    return self._generate_rotation_task(shape_a, shape_c, rotation_angle)
            
            # If we still can't find a unique combination after many attempts,
            # generate all remaining combinations systematically
            return self._generate_systematic_unique_combination()
        
        # If we've exhausted unique combinations, allow duplicates but warn
        if len(self.generated_combinations) == max_unique_combinations:
            print(f"⚠️  Warning: Generated all {max_unique_combinations} unique combinations. Allowing duplicates for remaining tasks.")
        
        shape_a, shape_c = random.sample(self.base_shapes, 2)
        rotation_angle = random.choice(self.rotation_angles)
        return self._generate_rotation_task(shape_a, shape_c, rotation_angle)
    
    def _generate_systematic_unique_combination(self) -> Dict[str, Any]:
        """Generate a unique combination systematically when random selection fails."""
        # Generate all possible combinations and find one not yet used
        for shape_a in self.base_shapes:
            for shape_c in self.base_shapes:
                if shape_a == shape_c:
                    continue
                for rotation_angle in self.rotation_angles:
                    combination_key = (shape_a, shape_c, rotation_angle)
                    if combination_key not in self.generated_combinations:
                        self.generated_combinations.add(combination_key)
                        return self._generate_rotation_task(shape_a, shape_c, rotation_angle)
        
        # This should never happen if our math is correct
        raise RuntimeError("Failed to generate unique combination - this should not happen!")
    
    def _generate_rotation_task(self, shape_a: str, shape_c: str, rotation_angle: float) -> Dict[str, Any]:
        """Generate a rotation transformation task."""
        return {
            "transformation_type": "rotation",
            "shape_a": shape_a,
            "shape_b": shape_a,  # Same shape, different rotation
            "shape_c": shape_c,
            "shape_d": shape_c,  # Same shape, different rotation
            "rotation_angle": rotation_angle,
            "description": f"{shape_a} rotated by {rotation_angle}°, {shape_c} rotated by {rotation_angle}°"
        }
    
    # ══════════════════════════════════════════════════════════════════════════
    #  IMAGE RENDERING
    # ══════════════════════════════════════════════════════════════════════════
    
    def _render_initial_state(self, task_data: Dict[str, Any]) -> Image.Image:
        """Render the initial state with A:B :: C:? layout."""
        img = self.renderer.create_blank_image()
        draw = ImageDraw.Draw(img)
        
        width, height = self.config.image_size
        margin = self.config.margin
        shape_size = self.config.shape_size
        
        # Layout positions
        # A    →    B
        # C    →    ?
        
        positions = {
            "A": (margin + shape_size//2, height//4),
            "arrow1": (width//2, height//4),
            "B": (width - margin - shape_size//2, height//4),
            "C": (margin + shape_size//2, 3*height//4),
            "arrow2": (width//2, 3*height//4),
            "question": (width - margin - shape_size//2, 3*height//4)
        }
        
        # Draw shapes and arrows - CRITICAL: Shape B shows the example rotation
        rotation_angle = task_data["rotation_angle"]  # Store once to ensure consistency
        
        self._draw_shape_at_position(draw, task_data["shape_a"], positions["A"], shape_size, 0)  # Original orientation
        self._draw_arrow(draw, positions["arrow1"])
        self._draw_shape_at_position(draw, task_data["shape_b"], positions["B"], shape_size, rotation_angle)  # Example rotation
        
        self._draw_shape_at_position(draw, task_data["shape_c"], positions["C"], shape_size, 0)  # Original orientation
        self._draw_arrow(draw, positions["arrow2"])
        self._draw_question_mark(draw, positions["question"])
        
        return img
    
    def _render_final_state(self, task_data: Dict[str, Any]) -> Image.Image:
        """Render the final state with the answer revealed."""
        img = self.renderer.create_blank_image()
        draw = ImageDraw.Draw(img)
        
        width, height = self.config.image_size
        margin = self.config.margin
        shape_size = self.config.shape_size
        
        # Same layout as initial state
        positions = {
            "A": (margin + shape_size//2, height//4),
            "arrow1": (width//2, height//4),
            "B": (width - margin - shape_size//2, height//4),
            "C": (margin + shape_size//2, 3*height//4),
            "arrow2": (width//2, 3*height//4),
            "D": (width - margin - shape_size//2, 3*height//4)
        }
        
        # Draw shapes and arrows - CRITICAL: Both B and D must use EXACTLY the same rotation angle
        rotation_angle = task_data["rotation_angle"]  # Store once to ensure consistency
        
        self._draw_shape_at_position(draw, task_data["shape_a"], positions["A"], shape_size, 0)  # Original orientation
        self._draw_arrow(draw, positions["arrow1"])
        self._draw_shape_at_position(draw, task_data["shape_b"], positions["B"], shape_size, rotation_angle)  # Rotated by EXACT angle
        
        self._draw_shape_at_position(draw, task_data["shape_c"], positions["C"], shape_size, 0)  # Original orientation
        self._draw_arrow(draw, positions["arrow2"])
        self._draw_shape_at_position(draw, task_data["shape_d"], positions["D"], shape_size, rotation_angle)  # Rotated by SAME EXACT angle
        
        return img
    
    def _draw_shape_at_position(self, draw: ImageDraw.Draw, shape: str, position: Tuple[int, int], size: int, rotation_angle: float):
        """Draw a shape at the specified position with the given rotation."""
        x, y = position
        self._draw_rotated_shape(draw, shape, x, y, size, self.shape_color, rotation_angle)
    
    def _draw_rotated_shape(self, draw: ImageDraw.Draw, shape: str, x: int, y: int, size: int, color: Tuple[int, int, int], rotation_angle: float):
        """Draw a shape with rotation applied."""
        half_size = size // 2
        
        # Convert rotation angle to radians
        angle_rad = math.radians(rotation_angle)
        
        if shape == "square":
            # Square vertices
            vertices = [
                (-half_size, -half_size),  # top-left
                (half_size, -half_size),   # top-right
                (half_size, half_size),    # bottom-right
                (-half_size, half_size)    # bottom-left
            ]
            rotated_vertices = self._rotate_points(vertices, angle_rad, x, y)
            draw.polygon(rotated_vertices, fill=color, outline=(0,0,0), width=2)
        
        elif shape == "triangle":
            # Triangle vertices (equilateral, pointing up)
            vertices = [
                (0, -half_size),           # top
                (-half_size, half_size),   # bottom-left
                (half_size, half_size)     # bottom-right
            ]
            rotated_vertices = self._rotate_points(vertices, angle_rad, x, y)
            draw.polygon(rotated_vertices, fill=color, outline=(0,0,0), width=2)
        
        elif shape == "diamond":
            # Diamond vertices
            vertices = [
                (0, -half_size),    # top
                (half_size, 0),     # right
                (0, half_size),     # bottom
                (-half_size, 0)     # left
            ]
            rotated_vertices = self._rotate_points(vertices, angle_rad, x, y)
            draw.polygon(rotated_vertices, fill=color, outline=(0,0,0), width=2)
        
        elif shape == "pentagon":
            # Pentagon vertices
            vertices = []
            for i in range(5):
                vertex_angle = i * 2 * math.pi / 5 - math.pi/2  # Start from top
                px = half_size * math.cos(vertex_angle)
                py = half_size * math.sin(vertex_angle)
                vertices.append((px, py))
            rotated_vertices = self._rotate_points(vertices, angle_rad, x, y)
            draw.polygon(rotated_vertices, fill=color, outline=(0,0,0), width=2)
        
        elif shape == "hexagon":
            # Hexagon vertices
            vertices = []
            for i in range(6):
                vertex_angle = i * 2 * math.pi / 6
                px = half_size * math.cos(vertex_angle)
                py = half_size * math.sin(vertex_angle)
                vertices.append((px, py))
            rotated_vertices = self._rotate_points(vertices, angle_rad, x, y)
            draw.polygon(rotated_vertices, fill=color, outline=(0,0,0), width=2)
        
        elif shape == "rectangle":
            # Rectangle vertices (wider than tall)
            width_factor = 1.4
            rect_width = int(half_size * width_factor)
            rect_height = int(half_size * 0.7)
            vertices = [
                (-rect_width, -rect_height),  # top-left
                (rect_width, -rect_height),   # top-right
                (rect_width, rect_height),    # bottom-right
                (-rect_width, rect_height)    # bottom-left
            ]
            rotated_vertices = self._rotate_points(vertices, angle_rad, x, y)
            draw.polygon(rotated_vertices, fill=color, outline=(0,0,0), width=2)
        
        elif shape == "star":
            # 5-pointed star vertices
            vertices = []
            outer_radius = half_size
            inner_radius = half_size * 0.4
            
            for i in range(10):  # 5 outer + 5 inner points
                if i % 2 == 0:  # Outer points
                    vertex_angle = i * math.pi / 5 - math.pi/2
                    px = outer_radius * math.cos(vertex_angle)
                    py = outer_radius * math.sin(vertex_angle)
                else:  # Inner points
                    vertex_angle = i * math.pi / 5 - math.pi/2
                    px = inner_radius * math.cos(vertex_angle)
                    py = inner_radius * math.sin(vertex_angle)
                vertices.append((px, py))
            
            rotated_vertices = self._rotate_points(vertices, angle_rad, x, y)
            draw.polygon(rotated_vertices, fill=color, outline=(0,0,0), width=2)
        
        elif shape == "heart":
            # Heart shape using curves (approximate with polygon)
            # This is a simplified heart shape
            vertices = [
                (0, half_size),                    # bottom point
                (-half_size*0.7, 0),              # left curve
                (-half_size*0.3, -half_size*0.5), # left top
                (0, -half_size*0.2),              # center top
                (half_size*0.3, -half_size*0.5),  # right top
                (half_size*0.7, 0),               # right curve
            ]
            rotated_vertices = self._rotate_points(vertices, angle_rad, x, y)
            draw.polygon(rotated_vertices, fill=color, outline=(0,0,0), width=2)
        
        elif shape == "octagon":
            # Octagon vertices
            vertices = []
            for i in range(8):
                vertex_angle = i * 2 * math.pi / 8
                px = half_size * math.cos(vertex_angle)
                py = half_size * math.sin(vertex_angle)
                vertices.append((px, py))
            rotated_vertices = self._rotate_points(vertices, angle_rad, x, y)
            draw.polygon(rotated_vertices, fill=color, outline=(0,0,0), width=2)
        
        elif shape == "trapezoid":
            # Trapezoid vertices (wider at bottom)
            top_width = half_size * 0.5
            vertices = [
                (-top_width, -half_size),     # top left
                (top_width, -half_size),      # top right
                (half_size, half_size),       # bottom right
                (-half_size, half_size)       # bottom left
            ]
            rotated_vertices = self._rotate_points(vertices, angle_rad, x, y)
            draw.polygon(rotated_vertices, fill=color, outline=(0,0,0), width=2)
        
        elif shape == "rhombus":
            # Rhombus vertices (diamond with different proportions)
            vertices = [
                (0, -half_size),              # top
                (half_size*0.7, 0),           # right
                (0, half_size),               # bottom
                (-half_size*0.7, 0)           # left
            ]
            rotated_vertices = self._rotate_points(vertices, angle_rad, x, y)
            draw.polygon(rotated_vertices, fill=color, outline=(0,0,0), width=2)
        
        elif shape == "plus":
            # Plus sign (thicker cross)
            thickness = half_size * 0.4
            vertices = [
                (-thickness, -half_size),      # top left
                (thickness, -half_size),       # top right
                (thickness, -thickness),       # inner top right
                (half_size, -thickness),       # right top
                (half_size, thickness),        # right bottom
                (thickness, thickness),        # inner bottom right
                (thickness, half_size),        # bottom right
                (-thickness, half_size),       # bottom left
                (-thickness, thickness),       # inner bottom left
                (-half_size, thickness),       # left bottom
                (-half_size, -thickness),      # left top
                (-thickness, -thickness),      # inner top left
            ]
            rotated_vertices = self._rotate_points(vertices, angle_rad, x, y)
            draw.polygon(rotated_vertices, fill=color, outline=(0,0,0), width=2)
        
        elif shape == "minus":
            # Minus sign (horizontal bar)
            thickness = half_size * 0.25
            vertices = [
                (-half_size, -thickness),      # left top
                (half_size, -thickness),       # right top
                (half_size, thickness),        # right bottom
                (-half_size, thickness),       # left bottom
            ]
            rotated_vertices = self._rotate_points(vertices, angle_rad, x, y)
            draw.polygon(rotated_vertices, fill=color, outline=(0,0,0), width=2)
        
        elif shape == "L_shape":
            # L shape
            thickness = half_size * 0.4
            vertices = [
                (-half_size, -half_size),      # outer top left
                (-half_size+thickness, -half_size),  # inner top left
                (-half_size+thickness, half_size-thickness),  # inner corner
                (half_size, half_size-thickness),    # inner top right
                (half_size, half_size),        # outer bottom right
                (-half_size, half_size),       # outer bottom left
            ]
            rotated_vertices = self._rotate_points(vertices, angle_rad, x, y)
            draw.polygon(rotated_vertices, fill=color, outline=(0,0,0), width=2)
        
        elif shape == "T_shape":
            # T shape
            thickness = half_size * 0.4
            vertices = [
                (-half_size, -half_size),      # top left
                (half_size, -half_size),       # top right
                (half_size, -half_size+thickness),  # inner top right
                (thickness/2, -half_size+thickness),  # inner stem right
                (thickness/2, half_size),      # stem bottom right
                (-thickness/2, half_size),     # stem bottom left
                (-thickness/2, -half_size+thickness),  # inner stem left
                (-half_size, -half_size+thickness),  # inner top left
            ]
            rotated_vertices = self._rotate_points(vertices, angle_rad, x, y)
            draw.polygon(rotated_vertices, fill=color, outline=(0,0,0), width=2)
        
        elif shape == "parallelogram":
            # Parallelogram vertices
            skew = half_size * 0.3
            vertices = [
                (-half_size+skew, -half_size),  # top left
                (half_size+skew, -half_size),   # top right
                (half_size-skew, half_size),    # bottom right
                (-half_size-skew, half_size)    # bottom left
            ]
            rotated_vertices = self._rotate_points(vertices, angle_rad, x, y)
            draw.polygon(rotated_vertices, fill=color, outline=(0,0,0), width=2)
        
        elif shape == "kite":
            # Kite vertices
            vertices = [
                (0, -half_size),               # top
                (half_size*0.4, -half_size*0.2),  # right upper
                (0, half_size*0.6),            # bottom
                (-half_size*0.4, -half_size*0.2)  # left upper
            ]
            rotated_vertices = self._rotate_points(vertices, angle_rad, x, y)
            draw.polygon(rotated_vertices, fill=color, outline=(0,0,0), width=2)
        
        elif shape == "chevron":
            # Chevron (V shape) vertices
            vertices = [
                (-half_size, -half_size*0.5),  # left top
                (0, half_size*0.5),            # bottom point
                (half_size, -half_size*0.5),   # right top
                (half_size*0.6, -half_size*0.8),  # right inner
                (0, half_size*0.1),            # inner bottom
                (-half_size*0.6, -half_size*0.8)  # left inner
            ]
            rotated_vertices = self._rotate_points(vertices, angle_rad, x, y)
            draw.polygon(rotated_vertices, fill=color, outline=(0,0,0), width=2)
        
        elif shape == "arrow":
            # Arrow pointing right
            vertices = [
                (-half_size, -half_size*0.3),     # left top
                (half_size*0.3, -half_size*0.3),  # shaft top
                (half_size*0.3, -half_size),      # arrow top
                (half_size, 0),                   # arrow tip
                (half_size*0.3, half_size),       # arrow bottom
                (half_size*0.3, half_size*0.3),   # shaft bottom
                (-half_size, half_size*0.3),      # left bottom
            ]
            rotated_vertices = self._rotate_points(vertices, angle_rad, x, y)
            draw.polygon(rotated_vertices, fill=color, outline=(0,0,0), width=2)
        
        elif shape == "cross":
            # Cross shape
            thickness = half_size * 0.3
            vertices = [
                (-thickness, -half_size),      # top left
                (thickness, -half_size),       # top right
                (thickness, -thickness),       # inner top right
                (half_size, -thickness),       # right top
                (half_size, thickness),        # right bottom
                (thickness, thickness),        # inner bottom right
                (thickness, half_size),        # bottom right
                (-thickness, half_size),       # bottom left
                (-thickness, thickness),       # inner bottom left
                (-half_size, thickness),       # left bottom
                (-half_size, -thickness),      # left top
                (-thickness, -thickness),      # inner top left
            ]
            rotated_vertices = self._rotate_points(vertices, angle_rad, x, y)
            draw.polygon(rotated_vertices, fill=color, outline=(0,0,0), width=2)
    
    def _rotate_points(self, points: List[Tuple[float, float]], angle: float, center_x: int, center_y: int) -> List[Tuple[int, int]]:
        """Rotate a list of points around a center point."""
        rotated = []
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        
        for px, py in points:
            # Rotate point
            rotated_x = px * cos_a - py * sin_a
            rotated_y = px * sin_a + py * cos_a
            
            # Translate to center
            final_x = int(rotated_x + center_x)
            final_y = int(rotated_y + center_y)
            
            rotated.append((final_x, final_y))
        
        return rotated
    
    def _draw_arrow(self, draw: ImageDraw.Draw, position: Tuple[int, int]):
        """Draw a right-pointing arrow."""
        x, y = position
        length = self.config.arrow_length
        
        # Arrow shaft
        draw.line([x-length//2, y, x+length//2-10, y], fill=(0,0,0), width=3)
        
        # Arrow head
        points = [
            (x+length//2, y),
            (x+length//2-15, y-8),
            (x+length//2-15, y+8)
        ]
        draw.polygon(points, fill=(0,0,0))
    
    def _draw_question_mark(self, draw: ImageDraw.Draw, position: Tuple[int, int]):
        """Draw a question mark."""
        x, y = position
        size = self.config.question_mark_size
        
        try:
            font = ImageFont.truetype("arial.ttf", size)
        except:
            font = ImageFont.load_default()
        
        # Get text bounds for centering
        bbox = draw.textbbox((0, 0), "?", font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        
        text_x = x - w // 2
        text_y = y - h // 2
        
        draw.text((text_x, text_y), "?", font=font, fill=(100, 100, 100))
    
    # ══════════════════════════════════════════════════════════════════════════
    #  VIDEO GENERATION
    # ══════════════════════════════════════════════════════════════════════════
    
    def _generate_video(self, first_image: Image.Image, final_image: Image.Image, task_id: str, task_data: Dict[str, Any]) -> str:
        """Generate ground truth video showing the transformation."""
        temp_dir = Path(tempfile.gettempdir()) / f"{self.config.domain}_videos"
        temp_dir.mkdir(parents=True, exist_ok=True)
        video_path = temp_dir / f"{task_id}_ground_truth.mp4"
        
        # Create animation frames
        frames = self._create_transformation_frames(first_image, final_image, task_data)
        
        result = self.video_generator.create_video_from_frames(frames, video_path)
        return str(result) if result else None
    
    def _create_transformation_frames(self, first_image: Image.Image, final_image: Image.Image, task_data: Dict[str, Any], hold_frames: int = 15, rotation_frames: int = 30) -> List[Image.Image]:
        """Create animation frames showing the rotation transformation."""
        frames = []
        
        # Hold initial state
        for _ in range(hold_frames):
            frames.append(first_image.copy())
        
        # Create rotation animation showing the shape gradually rotating
        frames.extend(self._create_rotation_morph_frames(task_data, rotation_frames))
        
        # Hold final state
        for _ in range(hold_frames):
            frames.append(final_image.copy())
        
        return frames
    
    def _create_rotation_morph_frames(self, task_data: Dict[str, Any], num_frames: int) -> List[Image.Image]:
        """Create frames showing the shape gradually rotating."""
        frames = []
        
        width, height = self.config.image_size
        margin = self.config.margin
        shape_size = self.config.shape_size
        
        # Position of the shape that's being transformed (bottom right - the answer position)
        answer_x = width - margin - shape_size//2
        answer_y = 3*height//4
        
        shape_c = task_data["shape_c"]
        target_rotation = task_data["rotation_angle"]
        
        for i in range(num_frames):
            # Create frame with static elements
            img = self.renderer.create_blank_image()
            draw = ImageDraw.Draw(img)
            
            # Draw static elements (A, arrow, B, C, arrow)
            positions = {
                "A": (margin + shape_size//2, height//4),
                "arrow1": (width//2, height//4),
                "B": (width - margin - shape_size//2, height//4),
                "C": (margin + shape_size//2, 3*height//4),
                "arrow2": (width//2, 3*height//4),
            }
            
            # Draw ALL static shapes - CRITICAL: Only the answer shape should rotate during animation
            static_rotation_angle = task_data["rotation_angle"]  # Fixed rotation for static shapes
            
            # Static shapes (A, B, C) and arrows - these NEVER change during animation
            self._draw_shape_at_position(draw, task_data["shape_a"], positions["A"], shape_size, 0)  # Always original
            self._draw_arrow(draw, positions["arrow1"])
            self._draw_shape_at_position(draw, task_data["shape_b"], positions["B"], shape_size, static_rotation_angle)  # Always rotated (example)
            self._draw_shape_at_position(draw, task_data["shape_c"], positions["C"], shape_size, 0)  # Always original
            self._draw_arrow(draw, positions["arrow2"])
            
            # ONLY the answer shape rotates during animation
            # Interpolate between 0 and target_rotation for ONLY this shape
            rotation_progress = i / (num_frames - 1) if num_frames > 1 else 1.0
            current_rotation = target_rotation * rotation_progress
            
            self._draw_rotated_shape(draw, shape_c, answer_x, answer_y, shape_size, self.shape_color, current_rotation)
            
            frames.append(img)
        
        return frames
