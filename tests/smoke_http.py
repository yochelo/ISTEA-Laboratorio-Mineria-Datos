"""Comprobación HTTP del contenedor que ejecuta el modelo aprobado."""

import json
import math
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import UUID

EJEMPLOS = Path(__file__).with_name("fixtures")
MODELO = "ISTEA_Churn/1"
SCORE = 0.9155293197461535


def solicitar(url, ejemplo=None):
    request = Request(url)
    if ejemplo:
        request = Request(
            url,
            data=(EJEMPLOS / ejemplo).read_bytes(),
            headers={"Content-Type": "application/json"},
        )
    try:
        respuesta = urlopen(request, timeout=3)
    except HTTPError as error:
        respuesta = error
    with respuesta:
        return respuesta.status, respuesta.headers, json.load(respuesta)


def main(base):
    for _ in range(30):
        try:
            estado, _, salud = solicitar(f"{base}/health")
        except (URLError, ConnectionError, TimeoutError):
            pass
        else:
            if estado == 200:
                break
        time.sleep(1)
    else:
        raise AssertionError("/health no devolvió HTTP 200 dentro del plazo")

    assert salud["model_version"] == MODELO, salud
    estado, cabeceras, cuerpo = solicitar(f"{base}/predict", "predict_request_valid.json")
    assert estado == 200 and cuerpo["model_version"] == MODELO, cuerpo
    assert math.isclose(cuerpo["probability"], SCORE, rel_tol=0, abs_tol=1e-12), cuerpo
    identificador = cabeceras.get("X-Request-ID")
    assert identificador and identificador == cuerpo["request_id"], cuerpo
    UUID(identificador)
    print(f"/health: 200 {MODELO} | /predict: 200 score={cuerpo['probability']}")

    estado, cabeceras, cuerpo = solicitar(f"{base}/predict", "predict_request_invalid.json")
    assert estado == 422 and cuerpo["detail"], cuerpo
    rechazo = cabeceras.get("X-Request-ID")
    assert rechazo and rechazo != identificador, "Identificador ausente o reutilizado"
    UUID(rechazo)
    print("/predict inválido: 422 con X-Request-ID propio")


if __name__ == "__main__":
    main(sys.argv[1])
