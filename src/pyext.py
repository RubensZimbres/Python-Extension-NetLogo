#!/usr/bin/env python

import os
import socket
import sys
import numbers
import json

if sys.version_info[0] > 2 and sys.version_info[1] > 3:
    from collections.abc import Mapping
else:
    from collections import Mapping

import traceback

# In
STMT_MSG = 0
EXPR_MSG = 1
ASSN_MSG = 2
EXPR_STRINGIFIED_MSG = 3

# Out
SUCC_MSG = 0
ERR_MSG = 1

class FlexibleEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, numbers.Integral):
            return int(o)
        if isinstance(o, numbers.Number):
            return float(o)
        if isinstance(o, Mapping):
            return dict(o)
        elif hasattr(o, '__len__') and hasattr(o, '__iter__'):
            return list(o)
        else:
            return json.JSONEncoder.default(self, o)  # let it error

def make_connection(sock):
    sock.bind(('localhost', 0))
    sock.listen(0)
    _, port = sock.getsockname()
    sys.stdout.write("{}\n".format(port))
    sys.stdout.flush()
    conn, addr = sock.accept()
    return conn

def parse(line):
    decoded = json.loads(line)
    type = decoded["type"]
    body = decoded["body"]
    return type, body

def logo_responder():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        conn = make_connection(sock)
        try:
            encoder = FlexibleEncoder()
            env_globals = {}
            for line in conn.makefile():
                try:
                    type, body = parse(line)

                    if type == STMT_MSG:
                        handle_statement(conn, body, env_globals, encoder)
                    elif type == EXPR_MSG:
                        handle_expression(conn, body, env_globals, encoder)
                    elif type == ASSN_MSG:
                        handle_assignment(conn, body, env_globals, encoder)
                    elif type == EXPR_STRINGIFIED_MSG:
                        handle_expression_stringified(conn, body, env_globals, encoder)
                except Exception as e:
                    handle_exception(conn, e, encoder)
                finally:
                    flush()
        finally:
            conn.close()
    finally:
        sock.close()



def handle_statement(conn, body, env_globals, encoder):
    exec(body, env_globals)
    conn.sendall(json.dumps({"type": SUCC_MSG, "body": ""}).encode('utf-8') + b"\n")


def handle_expression(conn, body, env_globals, encoder):
    evaluated = eval(body, env_globals)
    encoded = encoder.encode({"type": SUCC_MSG, "body": evaluated})
    conn.sendall(encoded.encode('utf-8') + b"\n")

def handle_assignment(conn, body, env_globals, encoder):
    varName = body["varName"]
    value = body["value"]
    env_globals[varName] = value
    conn.sendall(json.dumps({"type": SUCC_MSG, "body": ""}).encode('utf-8') + b"\n")

def handle_expression_stringified(conn, body, env_globals, encoder):
    if len(body.strip()) > 0:
        evaluated = repr(eval(body, env_globals))
    else:
        evaluated = ""
    encoded = encoder.encode({"type": SUCC_MSG, "body": evaluated})
    conn.sendall(encoded.encode('utf-8') + b"\n")

def handle_exception(conn, e, encoder):
    err_data = {"type": ERR_MSG, "body": {"message": str(e), "cause": traceback.format_exc()}}
    conn.sendall(encoder.encode(err_data).encode('utf-8') + b"\n")

def flush():
    sys.stdout.flush()
    sys.stderr.flush()

if __name__ == '__main__':
    sys.path.insert(0, os.getcwd())
    logo_responder()
