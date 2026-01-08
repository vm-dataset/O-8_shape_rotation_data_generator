# Shape Rotation Data Generator 🔄

A specialized data generator for creating synthetic **shape rotation transformation** tasks in the format A:B :: C:?. Perfect for training models on visual reasoning and analogical thinking with rotation transformations.

---

## 🚀 Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/your-org/shape-rotation-data-generator.git
cd shape-rotation-data-generator

# 2. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
pip install -e .

# 4. Generate tasks
python examples/generate.py --num-samples 50
```

---

## 📁 Structure

```
shape-rotation-data-generator/
├── core/                    # Framework utilities
│   ├── base_generator.py   # Abstract base class
│   ├── schemas.py          # Pydantic models
│   ├── image_utils.py      # Image helpers
│   ├── video_utils.py      # Video generation
│   └── output_writer.py    # File output
├── src/                     # Shape rotation implementation
│   ├── generator.py        # Rotation generator
│   ├── prompts.py          # Rotation prompts
│   └── config.py           # Rotation configuration
├── examples/
│   └── generate.py         # Entry point
└── data/questions/         # Generated output
    └── shape_rotation/     # Rotation task outputs
```

---

## 📦 Output Format

Every generator produces:

```
data/questions/shape_rotation/{task_id}/
├── first_frame.png          # Shows A→B :: C→? layout
├── final_frame.png          # Shows A→B :: C→D (answer)
├── prompt.txt               # Rotation transformation instruction
└── ground_truth.mp4         # Smooth rotation animation
```

---

## 🎯 Current Implementation: Rotation Transformations

The current implementation generates **visual analogy tasks** in the format **A:B :: C:?** focused on **shape rotation**.

### **Task Type:**
- **Rotation**: Angular transformations (30°, 45°, 60°, 90°, 120°, 135°, 150°, 180°)

### **Supported Shapes:**
- **Basic Shapes**: Square, Triangle, Diamond, Pentagon, Hexagon
- **Extended Shapes**: Rectangle, Star, Heart, Arrow, Cross
- All shapes support precise geometric rotation using trigonometry

### **Rotation Angles:**
- **30°**: Subtle rotation
- **45°**: Classic diagonal rotation
- **60°**: Clear angular change
- **90°**: Quarter turn
- **120°**: Two-thirds rotation
- **135°**: Three-quarter diagonal
- **150°**: Near-reverse rotation
- **180°**: Complete flip

### **Example Tasks:**
1. **45° Rotation**: `upright_square → 45°_square :: upright_triangle → 45°_triangle`
2. **90° Rotation**: `horizontal_rectangle → vertical_rectangle :: right_arrow → up_arrow`
3. **180° Rotation**: `upward_triangle → downward_triangle :: 5-point_star → inverted_star`

### **Features:**
- **Geometric Precision**: True mathematical rotation using rotation matrices
- **Smooth Animation**: Videos show gradual rotation over 30 frames
- **Clear Visual Layout**: A → B :: C → ? format with arrows
- **Rotation-Optimized Shapes**: Shapes chosen for maximum rotation visibility

---

## 🎨 Customization

This generator is specifically designed for shape rotation tasks. Key customizable parameters:

### Configuration (`src/config.py`)
- **Shapes**: 10 different rotation-friendly shapes
- **Rotation Angles**: 8 distinct angles from 30° to 180°
- **Image Size**: Default 512x512 with configurable margins
- **Video Settings**: Frame rate, animation duration

### Prompts (`src/prompts.py`)
- Rotation-specific instructions
- Multiple prompt variations for diversity

### Shape Rendering (`src/generator.py`)
- **Polygon-Based Drawing**: All shapes as rotatable polygons
- **Rotation Mathematics**: `_rotate_points()` method using trigonometry
- **Smooth Rotation Animation**: Gradual angle interpolation

### **Duplicate Prevention:**
The generator tracks unique combinations of:
- Shape A (first shape)
- Shape C (second shape) 
- Rotation angle

With 10 shapes and 8 rotation angles, there are **720 unique combinations** possible (10 × 9 × 8).

**Single entry point:** `python examples/generate.py --num-samples 50`

---

## 🔧 Usage Examples

```bash
# Generate 10 samples with videos
python examples/generate.py --num-samples 10

# Generate 50 samples without videos (faster)
python examples/generate.py --num-samples 50 --no-videos

# Custom output directory
python examples/generate.py --num-samples 20 --output data/my_rotation_dataset

# Generate large dataset
python examples/generate.py --num-samples 500 --no-videos
```

---

## 📊 Dataset Statistics

- **Total Possible Combinations**: 720 unique tasks
- **Shape Pairs**: 90 (10 shapes × 9 other shapes)
- **Rotation Angles**: 8 distinct angles
- **Task Complexity**: Medium (geometric rotation understanding)
- **Animation Quality**: Smooth rotation over 30 frames with trigonometric precision

---

## 🎬 Video Generation

Each task includes a ground truth video showing:
1. **Initial State** (15 frames): A:B :: C:? layout
2. **Rotation Animation** (30 frames): Shape at answer position gradually rotates from 0° to target angle
3. **Final State** (15 frames): Complete A:B :: C:D solution

The rotation animation uses precise mathematical interpolation to show smooth, realistic rotation transformations.