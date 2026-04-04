import os
import json as _json
import urllib.request
import urllib.parse
import urllib.error

from src.values.value import Value
from src.values.types.number import Number
from src.values.types.string import String
from src.values.types.dict import Dict
from src.values.types.module import Module
from src.values.function.stdlib import StdlibFunction
from src.values.convert import python_to_omi, omi_to_python
from src.run.runtime import RTResult
from src.main.symboltable import SymbolTable
from src.error.message.rt import RTError


# ---------------------------------------------------------------------------
# Response value type
# ---------------------------------------------------------------------------

class _ResponseJsonFunction(StdlibFunction):
    """Callable attached to Response objects: response.json()"""

    def __init__(self, raw_text):
        super().__init__("json")
        self._raw = raw_text

    def execute(self, args):
        if args:
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "response.json() takes no arguments",
                self.context,
            ))
        try:
            data = _json.loads(self._raw)
            return RTResult().success(python_to_omi(data))
        except Exception as e:
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                f"Response body is not valid JSON: {e}",
                self.context,
            ))

    def copy(self):
        copy = _ResponseJsonFunction(self._raw)
        copy.set_context(self.context)
        copy.set_pos(self.pos_start, self.pos_end)
        return copy

    def __repr__(self):
        return "<built-in method response.json>"


class HTTPResponse(Value):
    """
    Omi value returned by every http.* request function.

    Accessible attributes (via dot notation):
        .status   — Number  (HTTP status code)
        .text     — String  (raw response body)
        .headers  — Dict    (response headers)
        .json()   — callable that parses body as JSON → Dict/List/...
    """

    def __init__(self, status, text, headers_dict):
        super().__init__()
        self._members = {
            "status":  Number(status),
            "text":    String(text),
            "headers": headers_dict,
            "json":    _ResponseJsonFunction(text),
        }

    def get_member(self, name):
        value = self._members.get(name)
        if value is None:
            return None, RTError(
                self.pos_start, self.pos_end,
                f"Response has no attribute '{name}'. Available: status, text, headers, json",
                self.context,
            )
        return value, None

    def copy(self):
        copy = HTTPResponse(
            self._members["status"].value,
            self._members["text"].value,
            self._members["headers"].copy(),
        )
        copy.set_pos(self.pos_start, self.pos_end)
        copy.set_context(self.context)
        return copy

    def __repr__(self):
        return f"<Response [{self._members['status'].value}]>"

    def __str__(self):
        return self.__repr__()


# ---------------------------------------------------------------------------
# Internal HTTP helper
# ---------------------------------------------------------------------------

def _omi_headers_to_dict(headers_val):
    """Convert an Omi Dict (or null) to a plain Python dict of strings."""
    if not isinstance(headers_val, Dict):
        return {}
    result = {}
    for k, v in headers_val.entries.items():
        if isinstance(v, String):
            result[k] = v.value
        elif isinstance(v, Number):
            result[k] = str(int(v.value) if v.value == int(v.value) else v.value)
    return result


def _make_request(method, url, body=None, headers_val=None, timeout=30):
    """
    Send an HTTP request and return an HTTPResponse value.
    Raises RuntimeError on network/connection failure.
    """
    h = _omi_headers_to_dict(headers_val)

    data = None
    if body is not None and not isinstance(body, Number):
        if isinstance(body, Dict):
            data = _json.dumps(omi_to_python(body)).encode("utf-8")
            h.setdefault("Content-Type", "application/json")
        elif isinstance(body, String) and body.value:
            data = body.value.encode("utf-8")
            h.setdefault("Content-Type", "application/x-www-form-urlencoded")

    req = urllib.request.Request(url, data=data, headers=h, method=method.upper())

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status      = resp.status
            text        = resp.read().decode("utf-8", errors="replace")
            headers_omi = Dict({k: String(v) for k, v in dict(resp.headers).items()})
    except urllib.error.HTTPError as e:
        status      = e.code
        text        = e.read().decode("utf-8", errors="replace")
        headers_omi = Dict({k: String(v) for k, v in dict(e.headers).items()})
    except urllib.error.URLError as e:
        raise RuntimeError(f"Network error: {e.reason}")
    except Exception as e:
        raise RuntimeError(str(e))

    return HTTPResponse(status, text, headers_omi)


# ---------------------------------------------------------------------------
# Built-in function class
# ---------------------------------------------------------------------------

def _null():
    return Number(0)


class HTTPBuiltInFunction(StdlibFunction):
    def __init__(self, name):
        super().__init__(name)

    def copy(self):
        copy = HTTPBuiltInFunction(self.name)
        copy.set_context(self.context)
        copy.set_pos(self.pos_start, self.pos_end)
        return copy

    def __repr__(self):
        return f"<built-in function http.{self.name}>"

    # ------------------------------------------------------------------ GET
    def execute_get(self, exec_ctx):
        url     = exec_ctx.symbol_table.get("url")
        headers = exec_ctx.symbol_table.get("headers")
        if not isinstance(url, String):
            return RTResult().failure(RTError(self.pos_start, self.pos_end, "url must be a string", exec_ctx))
        try:
            return RTResult().success(_make_request("GET", url.value, headers_val=headers))
        except RuntimeError as e:
            return RTResult().failure(RTError(self.pos_start, self.pos_end, str(e), exec_ctx))

    execute_get.arg_names = ["url"]
    execute_get.opt_names = ["headers"]
    execute_get.opt_defaults_factory = lambda: [_null()]

    # ----------------------------------------------------------------- POST
    def execute_post(self, exec_ctx):
        url     = exec_ctx.symbol_table.get("url")
        body    = exec_ctx.symbol_table.get("body")
        headers = exec_ctx.symbol_table.get("headers")
        if not isinstance(url, String):
            return RTResult().failure(RTError(self.pos_start, self.pos_end, "url must be a string", exec_ctx))
        try:
            return RTResult().success(_make_request("POST", url.value, body=body, headers_val=headers))
        except RuntimeError as e:
            return RTResult().failure(RTError(self.pos_start, self.pos_end, str(e), exec_ctx))

    execute_post.arg_names = ["url", "body"]
    execute_post.opt_names = ["headers"]
    execute_post.opt_defaults_factory = lambda: [_null()]

    # ------------------------------------------------------------------ PUT
    def execute_put(self, exec_ctx):
        url     = exec_ctx.symbol_table.get("url")
        body    = exec_ctx.symbol_table.get("body")
        headers = exec_ctx.symbol_table.get("headers")
        if not isinstance(url, String):
            return RTResult().failure(RTError(self.pos_start, self.pos_end, "url must be a string", exec_ctx))
        try:
            return RTResult().success(_make_request("PUT", url.value, body=body, headers_val=headers))
        except RuntimeError as e:
            return RTResult().failure(RTError(self.pos_start, self.pos_end, str(e), exec_ctx))

    execute_put.arg_names = ["url", "body"]
    execute_put.opt_names = ["headers"]
    execute_put.opt_defaults_factory = lambda: [_null()]

    # ---------------------------------------------------------------- PATCH
    def execute_patch(self, exec_ctx):
        url     = exec_ctx.symbol_table.get("url")
        body    = exec_ctx.symbol_table.get("body")
        headers = exec_ctx.symbol_table.get("headers")
        if not isinstance(url, String):
            return RTResult().failure(RTError(self.pos_start, self.pos_end, "url must be a string", exec_ctx))
        try:
            return RTResult().success(_make_request("PATCH", url.value, body=body, headers_val=headers))
        except RuntimeError as e:
            return RTResult().failure(RTError(self.pos_start, self.pos_end, str(e), exec_ctx))

    execute_patch.arg_names = ["url", "body"]
    execute_patch.opt_names = ["headers"]
    execute_patch.opt_defaults_factory = lambda: [_null()]

    # --------------------------------------------------------------- DELETE
    def execute_delete(self, exec_ctx):
        url     = exec_ctx.symbol_table.get("url")
        headers = exec_ctx.symbol_table.get("headers")
        if not isinstance(url, String):
            return RTResult().failure(RTError(self.pos_start, self.pos_end, "url must be a string", exec_ctx))
        try:
            return RTResult().success(_make_request("DELETE", url.value, headers_val=headers))
        except RuntimeError as e:
            return RTResult().failure(RTError(self.pos_start, self.pos_end, str(e), exec_ctx))

    execute_delete.arg_names = ["url"]
    execute_delete.opt_names = ["headers"]
    execute_delete.opt_defaults_factory = lambda: [_null()]

    # ------------------------------------------------------------- REQUEST
    def execute_request(self, exec_ctx):
        method  = exec_ctx.symbol_table.get("method")
        url     = exec_ctx.symbol_table.get("url")
        body    = exec_ctx.symbol_table.get("body")
        headers = exec_ctx.symbol_table.get("headers")
        if not isinstance(method, String):
            return RTResult().failure(RTError(self.pos_start, self.pos_end, "method must be a string", exec_ctx))
        if not isinstance(url, String):
            return RTResult().failure(RTError(self.pos_start, self.pos_end, "url must be a string", exec_ctx))
        try:
            return RTResult().success(_make_request(method.value, url.value, body=body, headers_val=headers))
        except RuntimeError as e:
            return RTResult().failure(RTError(self.pos_start, self.pos_end, str(e), exec_ctx))

    execute_request.arg_names = ["method", "url"]
    execute_request.opt_names = ["body", "headers"]
    execute_request.opt_defaults_factory = lambda: [_null(), _null()]

    # ------------------------------------------------------------ DOWNLOAD
    def execute_download(self, exec_ctx):
        url  = exec_ctx.symbol_table.get("url")
        path = exec_ctx.symbol_table.get("path")
        if not isinstance(url, String):
            return RTResult().failure(RTError(self.pos_start, self.pos_end, "url must be a string", exec_ctx))
        if not isinstance(path, String):
            return RTResult().failure(RTError(self.pos_start, self.pos_end, "path must be a string", exec_ctx))
        try:
            urllib.request.urlretrieve(url.value, path.value)
            return RTResult().success(Number(0))
        except Exception as e:
            return RTResult().failure(RTError(self.pos_start, self.pos_end, f"Download failed: {e}", exec_ctx))

    execute_download.arg_names = ["url", "path"]

    # -------------------------------------------------------------- UPLOAD
    def execute_upload(self, exec_ctx):
        url        = exec_ctx.symbol_table.get("url")
        path       = exec_ctx.symbol_table.get("path")
        field_name = exec_ctx.symbol_table.get("field_name")

        if not isinstance(url, String):
            return RTResult().failure(RTError(self.pos_start, self.pos_end, "url must be a string", exec_ctx))
        if not isinstance(path, String):
            return RTResult().failure(RTError(self.pos_start, self.pos_end, "path must be a string", exec_ctx))

        field = field_name.value if isinstance(field_name, String) else "file"

        try:
            with open(path.value, "rb") as f:
                file_data = f.read()
        except OSError as e:
            return RTResult().failure(RTError(self.pos_start, self.pos_end, f"Cannot read file: {e}", exec_ctx))

        filename = os.path.basename(path.value)
        boundary = b"----OmiBoundary7a4f9b2c"

        body = (
            b"--" + boundary + b"\r\n"
            + f'Content-Disposition: form-data; name="{field}"; filename="{filename}"\r\n'.encode()
            + b"Content-Type: application/octet-stream\r\n\r\n"
            + file_data
            + b"\r\n--" + boundary + b"--\r\n"
        )

        headers = {"Content-Type": f"multipart/form-data; boundary={boundary.decode()}"}
        req = urllib.request.Request(url.value, data=body, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                status      = resp.status
                text        = resp.read().decode("utf-8", errors="replace")
                headers_omi = Dict({k: String(v) for k, v in dict(resp.headers).items()})
            return RTResult().success(HTTPResponse(status, text, headers_omi))
        except urllib.error.HTTPError as e:
            status      = e.code
            text        = e.read().decode("utf-8", errors="replace")
            headers_omi = Dict({k: String(v) for k, v in dict(e.headers).items()})
            return RTResult().success(HTTPResponse(status, text, headers_omi))
        except Exception as e:
            return RTResult().failure(RTError(self.pos_start, self.pos_end, f"Upload failed: {e}", exec_ctx))

    execute_upload.arg_names = ["url", "path", "field_name"]


# ---------------------------------------------------------------------------
# Module factory
# ---------------------------------------------------------------------------

def create_http_module():
    symbol_table = SymbolTable()
    for name in ("get", "post", "put", "patch", "delete", "request", "download", "upload"):
        symbol_table.set(name, HTTPBuiltInFunction(name))
    return Module("http", symbol_table)
