from src.stdlib.system import create_system_module
from src.stdlib.files import create_files_module
from src.stdlib.paths import create_paths_module
from src.stdlib.time import create_time_module
from src.stdlib.math import create_math_module
from src.stdlib.json import create_json_module
from src.stdlib.http import create_http_module

BUILTIN_MODULES = {
    "omi/system": create_system_module,
    "omi/files":  create_files_module,
    "omi/paths":  create_paths_module,
    "omi/time":   create_time_module,
    "omi/math":   create_math_module,
    "omi/json":   create_json_module,
    "omi/http":   create_http_module,
}
