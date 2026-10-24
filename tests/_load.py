"""Load the garden core on its own, without Home Assistant installed. The core is plain Python, which is what
lets the same files run in the Home Assistant integration and in other apps."""
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "garden_tracker"
for name, path in (("custom_components", ROOT.parent), ("custom_components.garden_tracker", ROOT)):
    pkg = types.ModuleType(name)
    pkg.__path__ = [str(path)]  # a stand-in package, so importing the core does not run the integration's __init__
    sys.modules[name] = pkg
