import os
import sys

# Permite `import collector`, `import storage`, `import modeling` etc. sem
# instalar o projeto como pacote — o código-fonte vive em src/ (ver plan.md).
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
