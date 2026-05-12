from pathlib import Path
from typing import Any, Dict, Iterable

import pandas as pd


class ExportadorVectorEstado:
    def __init__(self, filas: Iterable[Dict[str, Any]]) -> None:
        self.filas = list(filas)

    def a_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame(self.filas)

    def exportar_csv(self, ruta: str | Path) -> None:
        self.a_dataframe().to_csv(ruta, index=False, encoding="utf-8-sig")

    def exportar_xlsx(self, ruta: str | Path) -> None:
        self.a_dataframe().to_excel(ruta, index=False)
