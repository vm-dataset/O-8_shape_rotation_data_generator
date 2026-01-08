"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                           YOUR TASK PROMPTS                                   ║
║                                                                               ║
║  CUSTOMIZE THIS FILE to define prompts/instructions for your task.            ║
║  Prompts are selected based on task type and returned to the model.           ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import random


# ══════════════════════════════════════════════════════════════════════════════
#  DEFINE YOUR PROMPTS
# ══════════════════════════════════════════════════════════════════════════════

PROMPTS = {
    "default": [
        "Show the rotation transformation being applied to the second shape. The rotation should match the angular change shown in the example.",
        "Animate the rotation transformation where the shape rotates according to the established pattern. The question mark should smoothly transition to show the rotated version of the shape.",
        "Complete the visual analogy by showing what the second shape becomes when the same rotation transformation is applied.",
    ],
    
    "rotation": [
        "Show the rotation transformation being applied to the second shape. The rotation should match the angular change shown in the example.",
        "Animate the rotation transformation where the shape rotates according to the established pattern.",
        "Complete the analogy by revealing the rotated version of the second shape.",
    ],
}


def get_prompt(task_type: str = "default") -> str:
    """
    Select a random prompt for the given task type.
    
    Args:
        task_type: Type of task (key in PROMPTS dict)
        
    Returns:
        Random prompt string from the specified type
    """
    prompts = PROMPTS.get(task_type, PROMPTS["default"])
    return random.choice(prompts)


def get_all_prompts(task_type: str = "default") -> list[str]:
    """Get all prompts for a given task type."""
    return PROMPTS.get(task_type, PROMPTS["default"])
