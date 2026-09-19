
# Funciones para la carga de datos del proyecto

import pandas as pd

def load_data(path):
    return pd.read_csv(path)