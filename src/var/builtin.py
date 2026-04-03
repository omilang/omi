from src.stdlib.system import create_system_module
from src.stdlib.files import create_files_module
from src.stdlib.paths import create_paths_module
from src.stdlib.time import create_time_module
from src.stdlib.math import create_math_module

BUILTIN_MODULES = {
    "system": create_system_module,
    "files": create_files_module,
    "paths": create_paths_module,
    "time": create_time_module,
    "math": create_math_module,
}
