from src.stdlib.system import create_system_module
from src.stdlib.files import create_files_module
from src.stdlib.paths import create_paths_module
from src.stdlib.time import create_time_module
from src.stdlib.math import create_math_module
from src.stdlib.json import create_json_module
from src.stdlib.http import create_http_module
from src.stdlib.txt import create_txt_module
from src.stdlib.string import create_string_module
from src.stdlib.regex import create_regex_module
from src.stdlib.log import create_log_module

BUILTIN_MODULES = {
    "omi:system": create_system_module,
    "omi:files":  create_files_module,
    "omi:paths":  create_paths_module,
    "omi:time":   create_time_module,
    "omi:math":   create_math_module,
    "omi:json":   create_json_module,
    "omi:http":   create_http_module,
    "omi:txt":    create_txt_module,
    "omi:string": create_string_module,
    "omi:regex":  create_regex_module,
    "omi:log":    create_log_module,
}
