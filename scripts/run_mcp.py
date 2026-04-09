import sys
from pathlib import Path

# Ajouter le répertoire racine au path
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.mcp.serverMCP import mcp


if __name__ == "__main__":
	print("Lancement du serveur MCP OutilsImmo")
	#mcp.run()
	mcp.run(transport="http", host="0.0.0.0", port=8100)
