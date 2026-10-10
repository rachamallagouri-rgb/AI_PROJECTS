"""
Template: export an existing PyTorch .pth model to TorchScript.

You MUST replace build_model() with the exact architecture used during training.
Do not guess layer names or shapes.
"""
from pathlib import Path
import torch

SOURCE = Path("models/source_model.pth")
DEST = Path("models/exported_model.pt")


def build_model():
    raise NotImplementedError("Import and return your exact trained model architecture here")


model = build_model()
state = torch.load(SOURCE, map_location="cpu", weights_only=True)
if isinstance(state, dict) and "state_dict" in state:
    state = state["state_dict"]
model.load_state_dict(state)
model.eval()
scripted = torch.jit.script(model)
scripted.save(str(DEST))
print(f"Saved: {DEST}")
